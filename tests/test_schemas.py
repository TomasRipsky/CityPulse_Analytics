"""The raw table schemas in infra/gcp/schemas/ are the contract between Silver and BigQuery."""

import json
from datetime import date
from pathlib import Path

import pyarrow as pa
import pytest

from citypulse.citibike import TRIP_SCHEMA
from citypulse.openmeteo import to_table
from citypulse.warehouse import LOAD_AUDIT_SCHEMA, TABLES, bq_schema_from_arrow

SCHEMAS = Path(__file__).parents[1] / "infra" / "gcp" / "schemas"
FIXTURES = Path(__file__).parent / "fixtures" / "openmeteo"


def terraform_schema(table: str) -> list[dict]:
    fields = json.loads((SCHEMAS / f"{table}.json").read_text())
    return [{k: f[k] for k in ("name", "type", "mode")} for f in fields]


def silver_schema(source: str) -> pa.Schema:
    if source == "citibike":
        return TRIP_SCHEMA
    payload = json.loads((FIXTURES / f"{source}_2025-01-15.json").read_text())
    return to_table(source, payload, date(2025, 1, 15)).schema


@pytest.mark.parametrize("source", sorted(TABLES))
def test_silver_matches_the_raw_table(source):
    assert bq_schema_from_arrow(silver_schema(source)) == terraform_schema(TABLES[source])


def test_load_audit_matches_its_table():
    assert bq_schema_from_arrow(LOAD_AUDIT_SCHEMA) == terraform_schema("load_audit")


def test_every_raw_field_is_documented():
    for path in SCHEMAS.glob("*.json"):
        for field in json.loads(path.read_text()):
            assert field.get("description"), f"{path.name}: {field['name']} has no description"


def test_type_mapping():
    schema = pa.schema(
        [
            ("t", pa.timestamp("us", tz="UTC")),
            ("d", pa.date32()),
            ("f", pa.float64()),
            ("i", pa.int64()),
            ("s", pa.string()),
        ]
    )
    assert [f["type"] for f in bq_schema_from_arrow(schema)] == [
        "TIMESTAMP",
        "DATE",
        "FLOAT",
        "INTEGER",
        "STRING",
    ]
    with pytest.raises(TypeError):
        bq_schema_from_arrow(pa.schema([("x", pa.timestamp("us"))]))  # no zone: not an instant
