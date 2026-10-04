"""Load the lake's Silver into BigQuery's raw tables, one period at a time.

Each period (a day, or a month of trips) owns one partition of its table. A load replaces that
partition in a single job — `WRITE_TRUNCATE` on the partition decorator `table$YYYYMMDD` — so a
re-run never duplicates rows and a failed job leaves the old partition as it was. Only periods with
a manifest are loaded, and every load appends to `raw.load_audit` how many rows the manifest
promised and how many BigQuery wrote.
"""

from __future__ import annotations

import pyarrow as pa

TABLES = {"weather": "weather_hourly", "air_quality": "air_quality_hourly", "citibike": "trips"}

LOAD_AUDIT_SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("period", pa.string()),
        ("partition", pa.string()),
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
