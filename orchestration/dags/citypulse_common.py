"""Shared settings of the CityPulse DAGs. The pipeline code is not imported here: tasks call the
`citypulse` CLI and dbt from the locked environment baked into the image (/opt/citypulse/.venv),
so DAG parsing stays light and the code that runs is exactly the image's version."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from airflow.sdk import Asset

ENV = os.environ.get("CITYPULSE_ENV", "dev")
PROJECT = os.environ["CITYPULSE_BQ_PROJECT"]
LAKE = os.environ["CITYPULSE_LAKE_URI"]
REVISION = os.environ.get("CITYPULSE_REVISION", "unknown")
# A frozen dataset ends on this New York day; the DAGs then never schedule past it.
LAST_DAY = (
    date.fromisoformat(os.environ["CITYPULSE_LAST_DAY"])
    if os.environ.get("CITYPULSE_LAST_DAY")
    else None
)

VENV_BIN = "/opt/citypulse/.venv/bin"
CLI = f"{VENV_BIN}/citypulse"
DBT_DIR = "/opt/citypulse/transform"

# The raw tables, as Airflow Assets: load tasks declare them as outlets, the transform DAG is
# scheduled on them, so dbt runs when (and because) new data landed.
RAW = {
    table: Asset(f"bigquery://{PROJECT}/raw/{table}")
    for table in ("weather_hourly", "air_quality_hourly", "trips")
}

log = logging.getLogger("citypulse")


def on_failure(context) -> None:
    ti = context["ti"]
    log.error(
        "CityPulse FAILED: %s.%s (run %s, try %s, image %s) — logs: %s",
        ti.dag_id,
        ti.task_id,
        context["run_id"],
        ti.try_number,
        REVISION,
        ti.log_url,
    )


DEFAULT_ARGS = {
    "owner": "citypulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "on_failure_callback": on_failure,
}


def logged(command: str) -> str:
    """A bash command whose log starts with the image (git commit) it ran from."""
    return f"echo image $CITYPULSE_REVISION && {command}"


def run_moment(context):
    """When the run is "for": its logical date, or (manual runs without one) when it started."""
    return context.get("logical_date") or context["dag_run"].run_after
