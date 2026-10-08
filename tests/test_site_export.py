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
    assert sorted(written) == sorted([*EXPORTS, "summary.json", *(f"bi/{n}" for n in BI_EXPORTS)])
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
