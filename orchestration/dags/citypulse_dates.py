"""Which period a DAG run works on. Pure functions without Airflow: the repo's tests cover them."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def ny_day_for_run(run_at: datetime) -> date:
    """The New York day that ended before the run: a 06:00 UTC run is 01:00–02:00 in New York."""
    return run_at.astimezone(NY).date() - timedelta(days=1)


def trips_month_for_run(run_at: datetime) -> date:
    """First day of the month two months before the run: Citi Bike publishes ~6 weeks late."""
    months = run_at.year * 12 + run_at.month - 1 - 2
    return date(months // 12, months % 12 + 1, 1)


def daily_end_date(last_day: date) -> datetime:
    """end_date of the daily DAG for a dataset ending on `last_day`.

    Airflow treats end_date as exclusive, so it sits a few hours after the last run (06:00 UTC the
    next day, which ingests `last_day`) and well before the run after it.
    """
    run_day = last_day + timedelta(days=1)
    return datetime(run_day.year, run_day.month, run_day.day, 12, 0, tzinfo=UTC)


def monthly_end_date(last_day: date) -> datetime:
    """end_date of the monthly DAG: just after the run (15th, 06:00 UTC) that ingests the month of
    `last_day`, before the next month's run."""
    months = last_day.year * 12 + last_day.month - 1 + 2
    return datetime(months // 12, months % 12 + 1, 15, 12, 0, tzinfo=UTC)
