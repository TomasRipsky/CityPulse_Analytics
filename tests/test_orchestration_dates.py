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


def test_end_dates_include_the_last_run_and_exclude_the_next():
    from datetime import timedelta

    from citypulse_dates import daily_end_date, monthly_end_date

    last = date(2026, 8, 31)
    last_daily = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)  # ingests 31 August
    assert ny_day_for_run(last_daily) == last
    assert last_daily < daily_end_date(last) < last_daily + timedelta(days=1)

    last_monthly = datetime(2026, 10, 15, 6, 0, tzinfo=UTC)  # ingests August's trips
    assert trips_month_for_run(last_monthly) == date(2026, 8, 1)
    assert last_monthly < monthly_end_date(last) < datetime(2026, 11, 15, 6, 0, tzinfo=UTC)
