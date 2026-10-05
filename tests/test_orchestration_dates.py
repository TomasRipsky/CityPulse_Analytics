"""Date rules of the Airflow DAGs (pure functions: no Airflow needed to test them)."""

import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "orchestration" / "dags"))

from citypulse_dates import ny_day_for_run, trips_month_for_run  # noqa: E402


def test_a_daily_run_ingests_the_new_york_day_that_just_ended():
    # 06:00 UTC on 2 January is 01:00 in New York: 1 January is over.
    assert ny_day_for_run(datetime(2025, 1, 2, 6, 0, tzinfo=UTC)) == date(2025, 1, 1)
    # 06:00 UTC in July is 02:00 daylight time: same rule.
    assert ny_day_for_run(datetime(2025, 7, 2, 6, 0, tzinfo=UTC)) == date(2025, 7, 1)


def test_the_day_after_the_fall_back_night():
    assert ny_day_for_run(datetime(2025, 11, 3, 6, 0, tzinfo=UTC)) == date(2025, 11, 2)


def test_a_monthly_run_loads_trips_two_months_back():
    assert trips_month_for_run(datetime(2025, 3, 15, 6, 0, tzinfo=UTC)) == date(2025, 1, 1)
    assert trips_month_for_run(datetime(2026, 1, 15, 6, 0, tzinfo=UTC)) == date(2025, 11, 1)
    assert trips_month_for_run(datetime(2026, 2, 15, 6, 0, tzinfo=UTC)) == date(2025, 12, 1)
