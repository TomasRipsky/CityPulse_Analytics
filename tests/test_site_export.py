import json

import pyarrow as pa

from citypulse.site_export import BI_EXPORTS, EXPORTS, export


class FakeBigQuery:
    def __init__(self):
        self.queries = []

    def query(self, sql):
        self.queries.append(sql)
        table = pa.table({"date": ["2025-05-01"], "trips": [100]})

        class Job:
            def to_arrow(self):
                return table

        return Job()


def test_every_export_is_written_from_the_project_marts(tmp_path):
    client = FakeBigQuery()
    written = export(client, "citypulse-tr-prod", tmp_path)
    assert sorted(written) == sorted(
        [*EXPORTS, "summary.json", "bi/days.parquet", *(f"bi/{n}" for n in BI_EXPORTS)]
    )
    assert all("`citypulse-tr-prod.marts." in sql for sql in client.queries)
    assert (tmp_path / "daily.csv").read_text().splitlines()[0] == '"date","trips"'


def test_summary_is_json_built_from_the_daily_export(tmp_path):
    export(FakeBigQuery(), "citypulse-tr-prod", tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["trips"] == 100 and summary["first_day"] == summary["last_day"] == "2025-05-01"


def test_bi_exports_are_parquet_files_from_the_report_models(tmp_path):
    import pyarrow.parquet as pq

    client = FakeBigQuery()
    written = export(client, "citypulse-tr-prod", tmp_path)
    for name in BI_EXPORTS:
        assert f"bi/{name}" in written
        assert pq.read_table(tmp_path / "bi" / name).num_rows == 1
    bi_sql = [sql for sql in client.queries if ".marts.rpt_" in sql]
    assert len(bi_sql) == len(BI_EXPORTS)


def test_the_bi_calendar_is_parquet_with_a_real_date_type(tmp_path):
    # DuckDB in the browser sniffs CSV headers, and some browsers read the quotes as part of the
    # names: the BI page reads Parquet only.
    import pyarrow as pa
    import pyarrow.parquet as pq

    export(FakeBigQuery(), "citypulse-tr-prod", tmp_path)
    days = pq.read_table(tmp_path / "bi" / "days.parquet")
    assert days.schema.field("date").type == pa.date32()
    assert days.column("trips").to_pylist() == [100]


def test_the_bi_page_gives_duckdb_parquet_only():
    # Every table in the page's `sql:` front matter shares one DuckDB database: one table that
    # fails to load breaks every chart, and CSV headers are sniffed differently across browsers.
    from pathlib import Path

    page = (Path(__file__).parents[1] / "site" / "src" / "bi.md").read_text()
    front = page.split("---")[1]
    tables = [line.split(":", 1)[1].strip() for line in front.splitlines() if line.startswith("  ")]
    assert tables and all(path.endswith(".parquet") for path in tables), tables
