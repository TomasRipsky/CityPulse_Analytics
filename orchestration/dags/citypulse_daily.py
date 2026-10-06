"""Weather and air quality for the New York day that just ended: lake → BigQuery raw.

06:00 UTC is 01:00 (winter) or 02:00 (summer) in New York, so the previous day is complete.
Ingestion itself refuses a day that is not over, so a manual run at the wrong time fails loudly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task
from citypulse_common import CLI, DEFAULT_ARGS, LAKE, LAST_DAY, PROJECT, RAW, run_moment
from citypulse_dates import daily_end_date, ny_day_for_run

SOURCES = {"weather": "weather_hourly", "air-quality": "air_quality_hourly"}


@dag(
    dag_id="citypulse_daily",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 2, tzinfo=UTC),
    end_date=daily_end_date(LAST_DAY) if LAST_DAY else None,
    catchup=False,
    max_active_runs=16,
    # a hung task (lost network, a sleeping laptop) fails and retries instead of waiting forever
    default_args={**DEFAULT_ARGS, "execution_timeout": timedelta(minutes=20)},
    tags=["citypulse", "ingest", "load"],
    doc_md=__doc__,
)
def citypulse_daily():
    for source, table in SOURCES.items():
        name = source.replace("-", "_")

        @task.bash(task_id=f"ingest_{name}")
        def ingest(source=source, **context) -> str:
            day = ny_day_for_run(run_moment(context))
            return f"{CLI} ingest {source} --from {day} --lake {LAKE}"

        @task.bash(task_id=f"load_{name}", outlets=[RAW[table]])
        def load(source=source, **context) -> str:
            day = ny_day_for_run(run_moment(context))
            return f"{CLI} load {source} --from {day} --lake {LAKE} --project {PROJECT}"

        ingest() >> load()


citypulse_daily()
