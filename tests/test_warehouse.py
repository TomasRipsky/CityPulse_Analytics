from pathlib import Path
from types import SimpleNamespace

import pytest
from google.cloud import bigquery

from citypulse import lake as paths
from citypulse.ingest import ReconciliationError
from citypulse.lake import Lake
from citypulse.warehouse import NotReadyError, load_period, partition_id

PROJECT = "citypulse-tr-dev"


class FakeLake(Lake):
    """A local lake that reports gs:// URIs, as a bucket would."""

    def __init__(self, root):
        super().__init__(str(root))
        self.is_local = False

    def _prepare(self, rel):
        path = self._path(rel)
        Path(path).parent.mkdir(parents=True, exist_ok=True)  # local folders stand in for GCS
        return path

    def uri_of(self, rel):
        return f"gs://citypulse-tr-dev-lake/{rel}"


class FakeBigQuery:
    def __init__(self, output_rows):
        self.output_rows = output_rows
        self.uri_loads, self.json_loads = [], []

    def get_table(self, table_id):
        return SimpleNamespace(schema=[bigquery.SchemaField("x", "STRING")], table_id=table_id)

    def load_table_from_uri(self, uris, destination, job_config):
        self.uri_loads.append((uris, destination, job_config))
        return SimpleNamespace(result=lambda: None, output_rows=self.output_rows)

    def load_table_from_json(self, rows, destination, job_config):
        self.json_loads.append((rows, destination, job_config))
        return SimpleNamespace(result=lambda: None)


def write_manifest(lake, source, period, rows, silver):
    lake.write_json(
        paths.manifest_path(source, period),
        {
            "source": source,
            "period": period,
            "rows": rows,
            "silver": silver,
            "extracted_at": "2026-10-05T10:00:00+00:00",
        },
    )


@pytest.fixture
def lake(tmp_path):
    return FakeLake(tmp_path)


def test_partition_ids():
    assert partition_id("weather", "2025-01-15") == "20250115"
    assert partition_id("air_quality", "2025-11-02") == "20251102"
    assert partition_id("citibike", "2025-01") == "202501"


def test_a_month_replaces_its_own_partition(lake):
    silver = [
        "silver/citibike/month=2025-01/part-000.parquet",
        "silver/citibike/month=2025-01/part-001.parquet",
    ]
    write_manifest(lake, "citibike", "2025-01", 2124475, silver)
    client = FakeBigQuery(output_rows=2124475)
    audit = load_period("citibike", "2025-01", lake, client, PROJECT)

    ((uris, destination, config),) = client.uri_loads
    assert destination == "citypulse-tr-dev.raw.trips$202501"
    assert uris == [f"gs://citypulse-tr-dev-lake/{rel}" for rel in silver]
    assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert config.source_format == bigquery.SourceFormat.PARQUET
    assert [f.name for f in config.schema] == ["x"]  # the table's own schema, never autodetected
    assert audit["expected_rows"] == audit["loaded_rows"] == 2124475
    assert audit["partition"] == "202501" and audit["files"] == 2


def test_every_load_is_audited(lake):
    write_manifest(
        lake, "weather", "2025-03-09", 23, ["silver/weather/date=2025-03-09/part.parquet"]
    )
    client = FakeBigQuery(output_rows=23)
    load_period("weather", "2025-03-09", lake, client, PROJECT)
    ((rows, destination, config),) = client.json_loads
    assert destination == "citypulse-tr-dev.raw.load_audit"
    assert config.write_disposition == bigquery.WriteDisposition.WRITE_APPEND
    assert rows[0]["source"] == "weather" and rows[0]["period"] == "2025-03-09"
    assert rows[0]["manifest_extracted_at"] == "2026-10-05T10:00:00+00:00"


def test_a_period_without_a_manifest_is_not_ready(lake):
    client = FakeBigQuery(output_rows=0)
    with pytest.raises(NotReadyError):
        load_period("weather", "2025-01-15", lake, client, PROJECT)
    assert client.uri_loads == [] and client.json_loads == []


def test_a_short_load_is_audited_then_fails(lake):
    write_manifest(
        lake, "citibike", "2025-01", 100, ["silver/citibike/month=2025-01/part-000.parquet"]
    )
    client = FakeBigQuery(output_rows=99)
    with pytest.raises(ReconciliationError, match="99"):
        load_period("citibike", "2025-01", lake, client, PROJECT)
    assert client.json_loads[0][0][0]["loaded_rows"] == 99


def test_a_local_lake_cannot_be_loaded(tmp_path):
    lake = Lake(str(tmp_path))
    write_manifest(
        lake, "weather", "2025-01-15", 24, ["silver/weather/date=2025-01-15/part.parquet"]
    )
    with pytest.raises(ValueError, match="gs://"):
        load_period("weather", "2025-01-15", lake, FakeBigQuery(24), PROJECT)
