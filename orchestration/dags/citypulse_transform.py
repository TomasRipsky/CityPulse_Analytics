"""dbt build (models + every test) whenever new raw data landed.

Scheduled on the raw tables as Airflow Assets: any load task's success queues a run. One run at a
time; events that arrive during a run are handled by the next one, so a backfill does not cause
one build per day loaded.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task
from citypulse_common import DBT_DIR, DEFAULT_ARGS, ENV, RAW, VENV_BIN, logged


@dag(
    dag_id="citypulse_transform",
    # a day is ready when both daily tables landed; a month when its trips did
    schedule=((RAW["weather_hourly"] & RAW["air_quality_hourly"]) | RAW["trips"]),
    start_date=datetime(2025, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    # a hung task (lost network, a sleeping laptop) fails and retries instead of waiting forever
    default_args={**DEFAULT_ARGS, "execution_timeout": timedelta(minutes=60)},
    tags=["citypulse", "dbt"],
    doc_md=__doc__,
)
def citypulse_transform():
    @task.bash
    def dbt_build() -> str:
        return logged(f"cd {DBT_DIR} && {VENV_BIN}/dbt build --target {ENV} --profiles-dir .")

    dbt_build()


citypulse_transform()
