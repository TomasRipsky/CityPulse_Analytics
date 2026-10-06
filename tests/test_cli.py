from datetime import date

import pytest

from citypulse import cli
from citypulse.http import NotPublishedError


def test_days_are_inclusive():
    assert cli.days(date(2025, 1, 30), date(2025, 2, 2)) == [
        date(2025, 1, 30),
        date(2025, 1, 31),
        date(2025, 2, 1),
        date(2025, 2, 2),
    ]


def test_months_cross_the_year_end():
    assert cli.months(date(2025, 11, 1), date(2026, 1, 1)) == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
    ]


@pytest.mark.parametrize(
    "argv",
    [
        ["ingest", "weather", "--from", "2025-02-02", "--to", "2025-02-01"],
        ["ingest", "trips", "--from", "2025-03", "--to", "2025-01"],
        ["ingest", "snow", "--from", "2025-01-01"],
        ["ingest", "trips", "--from", "2025-13"],
    ],
)
def test_bad_arguments_are_usage_errors(argv):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2


def test_ingest_days_runs_each_day(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(
        cli,
        "ingest_day",
        lambda source, day, lake, http, now: seen.append((source, day)) or {"rows": 24},
    )
    code = cli.main(
        [
            "ingest",
            "air-quality",
            "--from",
            "2025-01-01",
            "--to",
            "2025-01-02",
            "--lake",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert seen == [("air_quality", date(2025, 1, 1)), ("air_quality", date(2025, 1, 2))]


def test_ingest_trips_defaults_to_a_single_month(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(
        cli, "ingest_month", lambda month, lake, http, workdir: seen.append(month) or {"rows": 1}
    )
    assert cli.main(["ingest", "trips", "--from", "2025-01", "--lake", str(tmp_path)]) == 0
    assert seen == [date(2025, 1, 1)]


def test_an_unpublished_month_exits_1_with_a_message(monkeypatch, tmp_path, capsys):
    def missing(month, lake, http, workdir):
        raise NotPublishedError(
            "https://s3.amazonaws.com/tripdata/203001-citibike-tripdata.zip: HTTP 403"
        )

    monkeypatch.setattr(cli, "ingest_month", missing)
    assert cli.main(["ingest", "trips", "--from", "2030-01", "--lake", str(tmp_path)]) == 1
    assert "not published" in capsys.readouterr().err


def test_the_lake_in_use_is_logged(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(cli, "ingest_month", lambda month, lake, http, workdir: {"rows": 1})
    with caplog.at_level("INFO", logger="citypulse"):
        cli.main(["ingest", "trips", "--from", "2025-01", "--lake", str(tmp_path)])
    assert f"lake: {tmp_path}" in caplog.text


def test_load_runs_each_period_against_the_project(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "bigquery_client", lambda project: f"client:{project}")
    monkeypatch.setattr(
        cli,
        "load_period",
        lambda source, period, lake, client, project: (
            seen.append((source, period, client)) or {"loaded_rows": 1}
        ),
    )
    argv = [
        "load",
        "trips",
        "--from",
        "2025-11",
        "--to",
        "2026-01",
        "--lake",
        "gs://b",
        "--project",
        "p",
    ]
    assert cli.main(argv) == 0
    assert seen == [
        ("citibike", "2025-11", "client:p"),
        ("citibike", "2025-12", "client:p"),
        ("citibike", "2026-01", "client:p"),
    ]


def test_load_needs_a_project(monkeypatch):
    monkeypatch.delenv("CITYPULSE_BQ_PROJECT", raising=False)
    with pytest.raises(SystemExit) as exc:
        cli.main(["load", "weather", "--from", "2025-01-01", "--lake", "gs://b"])
    assert exc.value.code == 2


def test_load_of_a_missing_period_exits_1(monkeypatch, capsys):
    from citypulse.warehouse import NotReadyError

    monkeypatch.setattr(cli, "bigquery_client", lambda project: None)

    def not_ready(*args):
        raise NotReadyError("weather 2025-01-01: no manifest")

    monkeypatch.setattr(cli, "load_period", not_ready)
    argv = ["load", "weather", "--from", "2025-01-01", "--lake", "gs://b", "--project", "p"]
    assert cli.main(argv) == 1
    assert "not ingested" in capsys.readouterr().err


def test_load_from_a_local_lake_is_a_usage_error(monkeypatch):
    monkeypatch.setattr(
        cli, "bigquery_client", lambda project: pytest.fail("no client for a usage error")
    )
    with pytest.raises(SystemExit) as exc:
        cli.main(["load", "weather", "--from", "2025-01-01", "--lake", ".lake", "--project", "p"])
    assert exc.value.code == 2
