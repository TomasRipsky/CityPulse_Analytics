import json

import pyarrow as pa

from citypulse.site_export import EXPORTS, export


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
    assert sorted(written) == sorted([*EXPORTS, "summary.json"])
    assert all("`citypulse-tr-prod.marts." in sql for sql in client.queries)
    assert (tmp_path / "daily.csv").read_text().splitlines()[0] == '"date","trips"'


def test_summary_is_json_built_from_the_daily_export(tmp_path):
    export(FakeBigQuery(), "citypulse-tr-prod", tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["trips"] == 100 and summary["first_day"] == summary["last_day"] == "2025-05-01"
