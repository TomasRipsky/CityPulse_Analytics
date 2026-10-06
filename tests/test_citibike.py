import io
import zipfile
from datetime import UTC, date, datetime

import pyarrow as pa
import pytest

from citypulse.citibike import TRIP_SCHEMA, convert, count_rows, trip_members, zip_url

HEADER = (
    "ride_id,rideable_type,started_at,ended_at,start_station_name,start_station_id,"
    "end_station_name,end_station_id,start_lat,start_lng,end_lat,end_lng,member_casual"
)
JAN = date(2025, 1, 1)


def row(ride_id, started, ended, start_id="6182.02", start_name="W 20 St & 7 Ave", lat="40.74"):
    return (
        f"{ride_id},electric_bike,{started},{ended},{start_name},{start_id},"
        f"E 10 St & 2 Ave,5746.02,{lat},-73.99,40.72,-73.98,member"
    )


def make_zip(members: dict[str, str]) -> zipfile.ZipFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return zipfile.ZipFile(io.BytesIO(buffer.getvalue()))


def csv_text(*rows, trailing_newline=True):
    text = "\n".join([HEADER, *rows])
    return text + "\n" if trailing_newline else text


def convert_all(zf, info, month=JAN):
    batches = []

    class Writer:
        def write_table(self, table):
            assert table.schema.equals(TRIP_SCHEMA)
            batches.append(table)

    rows = convert(zf, info, month, Writer())
    return rows, pa.concat_tables(batches) if batches else TRIP_SCHEMA.empty_table()


def test_zip_url():
    assert zip_url(JAN) == "https://s3.amazonaws.com/tripdata/202501-citibike-tripdata.zip"


def test_trip_members_are_every_trip_csv_in_name_order():
    zf = make_zip(
        {
            "202501-citibike-tripdata_2.csv": csv_text(),
            "202501-citibike-tripdata_1.csv": csv_text(),
            "__MACOSX/._202501-citibike-tripdata_1.csv": "junk",
            "readme.txt": "hello",
            "folder/": "",
        }
    )
    assert [m.filename for m in trip_members(zf)] == [
        "202501-citibike-tripdata_1.csv",
        "202501-citibike-tripdata_2.csv",
    ]


@pytest.mark.parametrize("trailing_newline", [True, False])
def test_count_rows_counts_data_lines(trailing_newline):
    text = csv_text(
        row("A", "2025-01-01 10:00:00.000", "2025-01-01 10:10:00.000"),
        row("B", "2025-01-01 11:00:00.000", "2025-01-01 11:10:00.000"),
        row("C", "2025-01-01 12:00:00.000", "2025-01-01 12:10:00.000"),
        trailing_newline=trailing_newline,
    )
    zf = make_zip({"t_1.csv": text})
    assert count_rows(zf, zf.getinfo("t_1.csv")) == 3


def test_count_rows_of_a_header_only_file_is_zero():
    zf = make_zip({"t_1.csv": csv_text()})
    assert count_rows(zf, zf.getinfo("t_1.csv")) == 0


def test_convert_turns_new_york_wall_time_into_utc():
    zf = make_zip(
        {
            "t_1.csv": csv_text(
                row("WINTER", "2025-01-15 14:52:26.542", "2025-01-15 15:00:00.000"),
                row("SUMMER", "2025-07-01 08:00:00.000", "2025-07-01 08:20:00.000"),
                row("FALLBACK", "2025-11-02 01:30:00.000", "2025-11-02 01:45:00.000"),
                row("SPRING", "2025-03-09 02:30:00.000", "2025-03-09 03:10:00.000"),
            )
        }
    )
    rows, table = convert_all(zf, zf.getinfo("t_1.csv"))
    started = dict(zip(table["ride_id"].to_pylist(), table["started_at"].to_pylist(), strict=True))
    assert rows == 4
    assert started["WINTER"] == datetime(2025, 1, 15, 19, 52, 26, 542000, tzinfo=UTC)
    assert started["SUMMER"] == datetime(2025, 7, 1, 12, 0, tzinfo=UTC)
    assert started["FALLBACK"] == datetime(2025, 11, 2, 5, 30, tzinfo=UTC)  # first 01:30 (EDT)
    assert started["SPRING"] == datetime(2025, 3, 9, 7, 0, tzinfo=UTC)  # gap → 03:00 EDT


def test_convert_keeps_blanks_as_nulls_and_ids_as_strings():
    zf = make_zip(
        {
            "t_1.csv": csv_text(
                row("A", "2025-01-01 10:00:00.000", "2025-01-01 10:10:00.000", start_id="JC024"),
                row("B", "2025-01-01 10:00:00.000", "2025-01-01 10:10:00.000", "", "", ""),
            )
        }
    )
    _, table = convert_all(zf, zf.getinfo("t_1.csv"))
    assert table["start_station_id"].to_pylist() == ["JC024", None]
    assert table["start_station_name"].to_pylist() == ["W 20 St & 7 Ave", None]
    assert table["start_lat"].to_pylist() == [40.74, None]


def test_convert_adds_source_month_and_file():
    zf = make_zip(
        {"t_2.csv": csv_text(row("A", "2025-01-31 23:59:00.000", "2025-02-01 00:10:00.000"))}
    )
    _, table = convert_all(zf, zf.getinfo("t_2.csv"))
    assert table["source_month"].to_pylist() == [JAN]
    assert table["source_file"].to_pylist() == ["t_2.csv"]


def test_convert_of_an_empty_member_writes_nothing():
    zf = make_zip({"t_1.csv": csv_text()})
    rows, table = convert_all(zf, zf.getinfo("t_1.csv"))
    assert rows == 0
    assert table.num_rows == 0


def test_a_trip_across_the_fall_back_hour_never_ends_before_it_starts():
    # Starts 01:55 daylight time, ends 01:10 *standard* time (15 minutes later in real time).
    zf = make_zip(
        {"t_1.csv": csv_text(row("X", "2025-11-02 01:55:00.000", "2025-11-02 01:10:00.000"))}
    )
    _, table = convert_all(zf, zf.getinfo("t_1.csv"))
    assert table["started_at"][0].as_py() == datetime(2025, 11, 2, 5, 55, tzinfo=UTC)
    assert table["ended_at"][0].as_py() == datetime(2025, 11, 2, 6, 10, tzinfo=UTC)


def test_a_trip_inside_the_repeated_hour_keeps_its_order():
    zf = make_zip(
        {"t_1.csv": csv_text(row("Y", "2025-11-02 01:10:00.000", "2025-11-02 01:40:00.000"))}
    )
    _, table = convert_all(zf, zf.getinfo("t_1.csv"))
    assert table["started_at"][0].as_py() == datetime(2025, 11, 2, 5, 10, tzinfo=UTC)
    assert table["ended_at"][0].as_py() == datetime(2025, 11, 2, 5, 40, tzinfo=UTC)
