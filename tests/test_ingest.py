import io
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from citypulse import ingest
from citypulse import lake as paths
from citypulse.http import Http, NotPublishedError
from citypulse.ingest import ReconciliationError, ingest_day, ingest_month
from citypulse.lake import Lake

FIXTURES = Path(__file__).parent / "fixtures" / "openmeteo"
DAY, JAN = date(2025, 1, 15), date(2025, 1, 1)
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
HEADER = (
    "ride_id,rideable_type,started_at,ended_at,start_station_name,start_station_id,"
    "end_station_name,end_station_id,start_lat,start_lng,end_lat,end_lng,member_casual\n"
)


def trips_csv(n: int, prefix: str) -> str:
    line = (
        "{p}{i},classic_bike,2025-01-02 08:00:00.000,2025-01-02 08:10:00.000,"
        "A,1,B,2,40.7,-74.0,40.7,-74.0,member\n"
    )
    return HEADER + "".join(line.format(p=prefix, i=i) for i in range(n))


def zip_bytes(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return buffer.getvalue()


def http_serving(zip_content: bytes | None = None) -> Http:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host.endswith("open-meteo.com"):
            source = "air_quality" if "air-quality" in request.url.host else "weather"
            day = request.url.params["start_date"]
            return httpx.Response(200, content=(FIXTURES / f"{source}_{day}.json").read_bytes())
        if zip_content is None:
            return httpx.Response(403)
        return httpx.Response(200, content=zip_content)

    return Http(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None)


@pytest.fixture
def lake(tmp_path):
    return Lake(str(tmp_path / "lake"))


def test_ingest_day_lands_bronze_silver_and_manifest(lake):
    manifest = ingest_day("weather", DAY, lake, http_serving(), now=NOW)
    bronze = json.loads(lake.read_bytes(paths.bronze_day("weather", DAY)))
    recorded = json.loads((FIXTURES / "weather_2025-01-15.json").read_text())
    assert bronze == recorded
    assert lake.read_table(paths.silver_day("weather", DAY)).num_rows == 24
    assert manifest == lake.read_json(paths.manifest_path("weather", "2025-01-15"))
    assert manifest["rows"] == 24
    assert manifest["source"] == "weather" and manifest["period"] == "2025-01-15"
    assert manifest["null_counts"]["temperature_2m"] == 0
    assert manifest["silver"] == [paths.silver_day("weather", DAY)]


def test_ingest_month_reads_every_csv_and_totals_them(lake, tmp_path):
    content = zip_bytes(
        {
            "202501-citibike-tripdata_2.csv": trips_csv(3, "b"),
            "202501-citibike-tripdata_1.csv": trips_csv(5, "a"),
        }
    )
    manifest = ingest_month(JAN, lake, http_serving(content), workdir=tmp_path)
    assert manifest["rows"] == 8
    assert [(f["name"], f["rows"]) for f in manifest["files"]] == [
        ("202501-citibike-tripdata_1.csv", 5),
        ("202501-citibike-tripdata_2.csv", 3),
    ]
    assert manifest["silver"] == [paths.silver_trips_part(JAN, 0), paths.silver_trips_part(JAN, 1)]
    assert sum(lake.read_table(p).num_rows for p in manifest["silver"]) == 8
    record = lake.read_json(paths.bronze_trips(JAN))  # the archive stays at its source
    assert record["url"] == "https://s3.amazonaws.com/tripdata/202501-citibike-tripdata.zip"
    assert record["size"] == len(content)
    assert [m["name"] for m in record["members"] if m["trip_csv"]] == [  # archive order, as is
        "202501-citibike-tripdata_2.csv",
        "202501-citibike-tripdata_1.csv",
    ]
    assert all(isinstance(m["crc32"], int) for m in record["members"])
    assert not any(rel.endswith(".zip") for rel in lake.list(""))
    assert lake.exists(paths.manifest_path("citibike", "2025-01"))
    assert not list(tmp_path.glob("*.zip"))  # the local download is cleaned up


def test_a_parser_that_loses_rows_blocks_the_manifest(lake, tmp_path, monkeypatch):
    real_convert = ingest.convert
    monkeypatch.setattr(ingest, "convert", lambda *a: real_convert(*a) - 1)
    content = zip_bytes({"m_1.csv": trips_csv(4, "a")})
    with pytest.raises(ReconciliationError, match="m_1.csv"):
        ingest_month(JAN, lake, http_serving(content), workdir=tmp_path)
    assert not lake.exists(paths.manifest_path("citibike", "2025-01"))


def test_a_crash_before_the_manifest_leaves_the_period_unmarked(lake, monkeypatch):
    ingest_day("weather", DAY, lake, http_serving(), now=NOW)

    def broken(rel, obj):
        raise OSError("disk full")

    monkeypatch.setattr(lake, "write_json", broken)
    with pytest.raises(OSError):
        ingest_day("weather", DAY, lake, http_serving(), now=NOW)
    assert not lake.exists(paths.manifest_path("weather", "2025-01-15"))  # the old one is gone too


def test_rerunning_a_month_removes_stale_parts(lake, tmp_path):
    three = zip_bytes({f"m_{i}.csv": trips_csv(1, str(i)) for i in (1, 2, 3)})
    ingest_month(JAN, lake, http_serving(three), workdir=tmp_path)
    two = zip_bytes({f"m_{i}.csv": trips_csv(1, str(i)) for i in (1, 2)})
    ingest_month(JAN, lake, http_serving(two), workdir=tmp_path)
    assert lake.list(paths.silver_trips_dir(JAN)) == [
        paths.silver_trips_part(JAN, 0),
        paths.silver_trips_part(JAN, 1),
    ]


def test_an_unpublished_month_writes_nothing(lake, tmp_path):
    with pytest.raises(NotPublishedError):
        ingest_month(JAN, lake, http_serving(None), workdir=tmp_path)
    assert lake.list("") == []


def test_a_zip_without_trip_csvs_is_an_error(lake, tmp_path):
    content = zip_bytes({"readme.txt": "nothing here"})
    with pytest.raises(ReconciliationError, match="no trip CSV"):
        ingest_month(JAN, lake, http_serving(content), workdir=tmp_path)
    assert not lake.exists(paths.manifest_path("citibike", "2025-01"))


def http_with_payload(mutate) -> Http:
    """Serves the recorded weather fixtures after passing them through `mutate`."""

    def handler(request: httpx.Request) -> httpx.Response:
        day = request.url.params["start_date"]
        data = json.loads((FIXTURES / f"weather_{day}.json").read_text())
        mutate(data)
        return httpx.Response(200, json=data)

    return Http(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None)


def test_bronze_is_the_response_as_received(lake):
    ingest_day("weather", DAY, lake, http_serving(), now=NOW)
    raw = (FIXTURES / "weather_2025-01-15.json").read_bytes()
    assert lake.read_bytes(paths.bronze_day("weather", DAY)) == raw


def test_a_payload_that_breaks_the_contract_keeps_the_last_good_day(lake):
    ingest_day("weather", DAY, lake, http_serving(), now=NOW)
    before = lake.read_bytes(paths.bronze_day("weather", DAY))
    with pytest.raises(ValueError, match="snowfall"):
        ingest_day(
            "weather", DAY, lake, http_with_payload(lambda d: d["hourly"].pop("snowfall")), now=NOW
        )
    assert lake.exists(paths.manifest_path("weather", "2025-01-15"))
    assert lake.read_bytes(paths.bronze_day("weather", DAY)) == before


def test_an_unpublished_rerun_keeps_the_last_good_month(lake, tmp_path):
    content = zip_bytes({"m_1.csv": trips_csv(3, "a")})
    ingest_month(JAN, lake, http_serving(content), workdir=tmp_path)
    with pytest.raises(NotPublishedError):
        ingest_month(JAN, lake, http_serving(None), workdir=tmp_path)
    assert lake.read_json(paths.manifest_path("citibike", "2025-01"))["rows"] == 3
    assert lake.read_json(paths.bronze_trips(JAN))["size"] == len(content)


def test_a_rerun_that_fails_reconciliation_keeps_the_last_good_month(lake, tmp_path, monkeypatch):
    good = zip_bytes({"m_1.csv": trips_csv(3, "a")})
    ingest_month(JAN, lake, http_serving(good), workdir=tmp_path)
    real_convert = ingest.convert
    monkeypatch.setattr(ingest, "convert", lambda *a: real_convert(*a) - 1)
    with pytest.raises(ReconciliationError):
        ingest_month(
            JAN, lake, http_serving(zip_bytes({"m_1.csv": trips_csv(5, "b")})), workdir=tmp_path
        )
    assert lake.read_json(paths.manifest_path("citibike", "2025-01"))["rows"] == 3
    assert lake.read_json(paths.bronze_trips(JAN))["size"] == len(good)
    assert lake.read_table(paths.silver_trips_part(JAN, 0)).num_rows == 3


@pytest.mark.parametrize(
    ("now", "allowed"),
    [
        (datetime(2025, 1, 16, 4, 59, tzinfo=UTC), False),  # 23:59 in New York on the 15th
        (datetime(2025, 1, 16, 5, 0, tzinfo=UTC), True),  # midnight in New York: the day is over
    ],
)
def test_a_day_is_only_ingested_once_it_is_over(lake, now, allowed):
    if allowed:
        assert ingest_day("weather", DAY, lake, http_serving(), now=now)["rows"] == 24
    else:
        with pytest.raises(ValueError, match="not over"):
            ingest_day("weather", DAY, lake, http_serving(), now=now)
        assert lake.list("") == []
