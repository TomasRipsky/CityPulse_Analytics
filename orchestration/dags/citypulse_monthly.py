"""Citi Bike trips for the month two months back: lake → BigQuery raw.

Citi Bike publishes a month roughly six weeks after it ends, on no fixed day; on the 15th, the
month before last is reliably there. A month not yet published fails as "not published" and is
retried by the next run or by hand — nothing half-written is left behind.
"""

from __future__ import annotations

from datetime import UTC, datetime

from airflow.sdk import dag, task
from citypulse_common import CLI, DEFAULT_ARGS, LAKE, LAST_DAY, PROJECT, RAW, run_moment
from citypulse_dates import last_monthly_run, trips_month_for_run


@dag(
    dag_id="citypulse_monthly",
    schedule="0 6 15 * *",
    start_date=datetime(2025, 3, 15, tzinfo=UTC),
    end_date=last_monthly_run(LAST_DAY) if LAST_DAY else None,
    catchup=False,
    max_active_runs=2,
    default_args=DEFAULT_ARGS,
    tags=["citypulse", "ingest", "load"],
    doc_md=__doc__,
)
def citypulse_monthly():
    @task.bash
    def ingest_trips(**context) -> str:
        month = trips_month_for_run(run_moment(context))
        return f"{CLI} ingest trips --from {month:%Y-%m} --lake {LAKE}"

    @task.bash(outlets=[RAW["trips"]])
    def load_trips(**context) -> str:
        month = trips_month_for_run(run_moment(context))
        return f"{CLI} load trips --from {month:%Y-%m} --lake {LAKE} --project {PROJECT}"

    ingest_trips() >> load_trips()


citypulse_monthly()
