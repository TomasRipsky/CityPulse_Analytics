"""Citi Bike trip data: one ZIP per month on a public S3 bucket, holding one CSV per million trips.

Every CSV in the archive is a slice of the month — the archive's own order is arbitrary, so we
read all of them, in name order. Each CSV is streamed in blocks to Parquet, so memory stays flat
however large the month is. Trip times are New York wall-clock readings without an offset; they
become UTC instants here (on the fall-back night the repeated hour is read as its first, daylight
occurrence; a reading inside the spring-forward gap becomes 03:00 daylight time).

`count_rows` counts the lines of the raw CSV bytes, independently of the parser: it is the source's
control total that the parser's output must match.
"""

from __future__ import annotations

import zipfile
from datetime import date
from typing import Protocol

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv

BASE_URL = "https://s3.amazonaws.com/tripdata"
TIMEZONE = "America/New_York"
BLOCK_SIZE = 16 << 20  # bytes of CSV per batch (~80k trips); peak memory stays ~0.4 GB per file

CSV_TYPES = {
    "ride_id": pa.string(),
    "rideable_type": pa.string(),
    "started_at": pa.timestamp("ms"),
    "ended_at": pa.timestamp("ms"),
    "start_station_name": pa.string(),
    "start_station_id": pa.string(),
    "end_station_name": pa.string(),
    "end_station_id": pa.string(),
    "start_lat": pa.float64(),
    "start_lng": pa.float64(),
    "end_lat": pa.float64(),
    "end_lng": pa.float64(),
    "member_casual": pa.string(),
}
UTC_US = pa.timestamp("us", tz="UTC")
TRIP_SCHEMA = pa.schema(
    [
        *(
            pa.field(name, UTC_US if name in ("started_at", "ended_at") else kind)
            for name, kind in CSV_TYPES.items()
        ),
        pa.field("source_month", pa.date32()),
        pa.field("source_file", pa.string()),
    ]
)


class TableWriter(Protocol):
    def write_table(self, table: pa.Table) -> None: ...


def zip_url(month: date) -> str:
    return f"{BASE_URL}/{month:%Y%m}-citibike-tripdata.zip"


def trip_members(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """The trip CSVs in the archive, in name order (macOS metadata and other files skipped)."""
    members = [
        info
        for info in zf.infolist()
        if not info.is_dir()
        and info.filename.lower().endswith(".csv")
        and not info.filename.startswith("__MACOSX/")
    ]
    return sorted(members, key=lambda info: info.filename)


def count_rows(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> int:
    """Data rows in a CSV member: its lines minus the header, counted on the raw bytes."""
    lines, last = 0, b"\n"
    with zf.open(info) as handle:
        while chunk := handle.read(1 << 20):
            lines += chunk.count(b"\n")
            last = chunk[-1:]
    if last != b"\n":  # a final line without a newline still counts
        lines += 1
    return max(lines - 1, 0)


def convert(zf: zipfile.ZipFile, info: zipfile.ZipInfo, month: date, writer: TableWriter) -> int:
    """Stream one CSV member into `writer` as TRIP_SCHEMA batches; return the rows written."""
    rows = 0
    with zf.open(info) as handle:
        reader = csv.open_csv(
            handle,
            # no read-ahead threads: same speed here, ~100 MB less peak memory
            read_options=csv.ReadOptions(block_size=BLOCK_SIZE, use_threads=False),
            convert_options=csv.ConvertOptions(
                column_types=CSV_TYPES,
                include_columns=list(CSV_TYPES),
                strings_can_be_null=True,
            ),
        )
        for batch in reader:
            if batch.num_rows == 0:
                continue
            columns = {name: batch.column(name) for name in CSV_TYPES}
            for name in ("started_at", "ended_at"):
                local = pc.assume_timezone(
                    columns[name], TIMEZONE, ambiguous="earliest", nonexistent="latest"
                )
                columns[name] = local.cast(UTC_US)
            columns["source_month"] = pa.repeat(pa.scalar(month, pa.date32()), batch.num_rows)
            columns["source_file"] = pa.repeat(pa.scalar(info.filename), batch.num_rows)
            writer.write_table(pa.Table.from_pydict(columns, schema=TRIP_SCHEMA))
            rows += batch.num_rows
    return rows
