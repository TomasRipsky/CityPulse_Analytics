"""Which period a DAG run works on. Pure functions without Airflow: the repo's tests cover them."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def ny_day_for_run(run_at: datetime) -> date:
    """The New York day that ended before the run: a 06:00 UTC run is 01:00–02:00 in New York."""
    return run_at.astimezone(NY).date() - timedelta(days=1)


def trips_month_for_run(run_at: datetime) -> date:
    """First day of the month two months before the run: Citi Bike publishes ~6 weeks late."""
    months = run_at.year * 12 + run_at.month - 1 - 2
    return date(months // 12, months % 12 + 1, 1)
