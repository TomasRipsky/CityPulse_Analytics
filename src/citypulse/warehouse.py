"""Load the lake's Silver into BigQuery's raw tables, one period at a time.

Each period (a day, or a month of trips) owns one partition of its table. A load replaces that
partition in a single job — `WRITE_TRUNCATE` on the partition decorator `table$YYYYMMDD` — so a
re-run never duplicates rows and a failed job leaves the old partition as it was. Only periods with
a manifest are loaded; the Silver files are checked against the manifest's row count before the
job, and every completed load appends to `raw.load_audit` how many rows the manifest promised and
how many BigQuery wrote.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pyarrow as pa
from google.cloud import bigquery

from citypulse import lake as paths
from citypulse.ingest import ReconciliationError
from citypulse.lake import Lake

DATASET = "raw"

TABLES = {"weather": "weather_hourly", "air_quality": "air_quality_hourly", "citibike": "trips"}

LOAD_AUDIT_SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("period", pa.string()),
        ("partition_id", pa.string()),
        ("expected_rows", pa.int64()),
        ("loaded_rows", pa.int64()),
        ("files", pa.int64()),
        ("manifest_extracted_at", pa.timestamp("us", tz="UTC")),
        ("loaded_at", pa.timestamp("us", tz="UTC")),
    ]
)


def _bq_type(kind: pa.DataType) -> str:
    if pa.types.is_timestamp(kind):
        if kind.tz != "UTC":
            raise TypeError(f"{kind}: only UTC timestamps are instants BigQuery can store")
        return "TIMESTAMP"
    if pa.types.is_date32(kind):
        return "DATE"
    if pa.types.is_float64(kind):
        return "FLOAT"
    if pa.types.is_int64(kind):
        return "INTEGER"
    if pa.types.is_string(kind):
        return "STRING"
    raise TypeError(f"no BigQuery type mapped for {kind}")


def bq_schema_from_arrow(schema: pa.Schema) -> list[dict[str, str]]:
    """The BigQuery JSON schema (name, type, mode) an Arrow schema loads into."""
    return [{"name": f.name, "type": _bq_type(f.type), "mode": "NULLABLE"} for f in schema]


class NotReadyError(Exception):
    """The period has no manifest in the lake: it was never ingested, or its ingestion failed."""


def partition_id(source: str, period: str) -> str:
    """`2025-01-15` → `20250115` (daily sources); `2025-01` → `202501` (trips)."""
    return period.replace("-", "")


def load_period(
    source: str, period: str, lake: Lake, client: bigquery.Client, project: str
) -> dict[str, Any]:
    """Replace the period's partition with its Silver files; audit and reconcile the row count."""
    if lake.is_local:
        raise ValueError("BigQuery loads from gs:// only; point --lake at the GCS bucket")
    manifest_rel = paths.manifest_path(source, period)
    if not lake.exists(manifest_rel):
        raise NotReadyError(f"{source} {period}: no manifest in {lake.uri} (not ingested yet?)")
    manifest = lake.read_json(manifest_rel)
    # Check the files against the manifest before touching the table: a mismatch must never
    # replace a good partition.
    silver_rows = sum(lake.parquet_rows(rel) for rel in manifest["silver"])
    if silver_rows != manifest["rows"]:
        raise ReconciliationError(
            f"{source} {period}: manifest has {manifest['rows']} rows, "
            f"Silver files hold {silver_rows}"
        )

    table_id = f"{project}.{DATASET}.{TABLES[source]}"
    partition = partition_id(source, period)
    job = client.load_table_from_uri(
        [lake.uri_of(rel) for rel in manifest["silver"]],
        f"{table_id}${partition}",
        job_config=bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=client.get_table(table_id).schema,
        ),
    )
    job.result()

    audit = {
        "source": source,
        "period": period,
        "partition_id": partition,
        "expected_rows": manifest["rows"],
        "loaded_rows": job.output_rows,
        "files": len(manifest["silver"]),
        "manifest_extracted_at": manifest["extracted_at"],
        "loaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    client.load_table_from_json(
        [audit],
        f"{project}.{DATASET}.load_audit",
        job_config=bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=client.get_table(f"{project}.{DATASET}.load_audit").schema,
        ),
    ).result()
    if job.output_rows != manifest["rows"]:
        raise ReconciliationError(
            f"{source} {period}: manifest has {manifest['rows']} rows, "
            f"BigQuery loaded {job.output_rows}"
        )
    return audit
