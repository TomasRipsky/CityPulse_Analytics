from datetime import date

import pyarrow as pa

from citypulse import lake as paths
from citypulse.lake import Lake


def test_bytes_and_json_round_trip(tmp_path):
    lake = Lake(str(tmp_path))
    lake.write_bytes("a/b.bin", b"\x00\x01")
    lake.write_json("a/c.json", {"rows": 3})
    assert lake.read_bytes("a/b.bin") == b"\x00\x01"
    assert lake.read_json("a/c.json") == {"rows": 3}


def test_parquet_writer_round_trip(tmp_path):
    lake = Lake(str(tmp_path))
    table = pa.table({"x": [1, 2, 3]})
    with lake.parquet_writer("t/part.parquet", table.schema) as writer:
        writer.write_table(table)
    assert lake.read_table("t/part.parquet").equals(table)


def test_root_with_spaces(tmp_path):
    lake = Lake(str(tmp_path / "with spaces"))
    lake.write_bytes("x.txt", b"ok")
    assert lake.exists("x.txt")
    assert (tmp_path / "with spaces" / "x.txt").read_bytes() == b"ok"


def test_put_file_copies_a_local_file(tmp_path):
    source = tmp_path / "src.zip"
    source.write_bytes(b"zipbytes")
    lake = Lake(str(tmp_path / "lake"))
    lake.put_file("bronze/x.zip", source)
    assert lake.read_bytes("bronze/x.zip") == b"zipbytes"


def test_list_returns_files_under_prefix_sorted(tmp_path):
    lake = Lake(str(tmp_path))
    for rel in ("s/m=1/part-001.parquet", "s/m=1/part-000.parquet", "s/m=2/part-000.parquet"):
        lake.write_bytes(rel, b"")
    assert lake.list("s/m=1") == ["s/m=1/part-000.parquet", "s/m=1/part-001.parquet"]
    assert lake.list("missing") == []


def test_delete_and_delete_dir(tmp_path):
    lake = Lake(str(tmp_path))
    lake.write_bytes("d/one", b"")
    lake.write_bytes("d/two", b"")
    lake.delete("d/one")
    assert not lake.exists("d/one")
    lake.delete("d/one")  # deleting what is not there is fine
    lake.delete_dir("d")
    assert lake.list("d") == []
    lake.delete_dir("d")


def test_uri_of_local_is_a_path(tmp_path):
    assert Lake(str(tmp_path)).uri_of("a/b") == f"{tmp_path.resolve()}/a/b"


def test_layout():
    day, month = date(2025, 1, 15), date(2025, 1, 1)
    assert paths.bronze_day("weather", day) == "bronze/weather/date=2025-01-15/weather.json"
    assert paths.bronze_trips(month) == "bronze/citibike/month=2025-01/202501-citibike-tripdata.zip"
    assert paths.silver_day("air_quality", day) == (
        "silver/air_quality/date=2025-01-15/part.parquet"
    )
    assert paths.silver_trips_dir(month) == "silver/citibike/month=2025-01"
    assert paths.silver_trips_part(month, 3) == "silver/citibike/month=2025-01/part-003.parquet"
    assert paths.manifest_path("weather", "2025-01-15") == "_manifests/weather/2025-01-15.json"
    assert paths.manifest_path("citibike", "2025-01") == "_manifests/citibike/2025-01.json"
