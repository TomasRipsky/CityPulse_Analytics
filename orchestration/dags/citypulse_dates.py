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


def last_daily_run(last_day: date) -> datetime:
    """The daily run (06:00 UTC) that ingests `last_day`: the end_date of a frozen dataset."""
    run_day = last_day + timedelta(days=1)
    return datetime(run_day.year, run_day.month, run_day.day, 6, 0, tzinfo=UTC)


def last_monthly_run(last_day: date) -> datetime:
    """The monthly run (15th, 06:00 UTC) that ingests the month of `last_day`."""
    months = last_day.year * 12 + last_day.month - 1 + 2
    return datetime(months // 12, months % 12 + 1, 15, 6, 0, tzinfo=UTC)
