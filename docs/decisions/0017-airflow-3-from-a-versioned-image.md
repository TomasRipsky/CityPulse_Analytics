# 0017 — Airflow 3 locally, from a versioned image

- **Status:** Accepted
- **Date:** 2026-10-05
- **Supersedes:** [0003](0003-airflow-on-a-free-tier-vm.md)

## Context
Version 1 ran Airflow 2.8 on an always-on free-tier VM, installed by hand, with tasks that ran
`git pull` before importing the code — so two tasks of one run could execute different code, and
nothing reported a failure outside the UI. Airflow 2 reached end of life in April 2026. The v2
dataset is frozen (16 months, January 2025 – April 2026): it needs an orchestrator for the backfill and for
anyone who wants to run the pipeline, not a scheduler that runs forever.

## Decision
- **Airflow 3.3**, run on the operator's machine with Docker Compose — adapted from the official
  compose file: LocalExecutor (postgres, API server, scheduler, DAG processor, triggerer; no Celery),
  UI on 127.0.0.1 only.
- **The image is the deployment**: `orchestration/Dockerfile` builds on `apache/airflow:3.3.2`
  and adds the `citypulse` package and dbt in their **own environment, from the lock file**, plus
  the DAGs. Tasks call the CLI and dbt from that environment; DAG files import none of the pipeline
  code. The image is labelled with the git commit it was built from (`-dirty` if the tree had
  changes).
- **Three DAGs:** `citypulse_daily` (06:00 UTC: weather and air quality for the New York day that
  just ended), `citypulse_monthly` (the 15th: trips two months back), and `citypulse_transform`
  (dbt build, scheduled on the raw tables as **Airflow Assets** — it runs because new data landed,
  one run at a time).
- **The freeze is in code:** `CITYPULSE_LAST_DAY` becomes the DAGs' `end_date`, so a running
  Airflow never schedules past the dataset.
- Credentials: the host's Application Default Credentials, mounted read-only — ideally
  impersonating the pipeline service account (decision 0012).

## Alternatives considered
- Cloud Composer — managed, but hundreds of euros a month for a frozen dataset.
- A VM again — always-on compute and hand-made state.
- GitHub Actions as the scheduler — free, but no task graph, backfill or asset scheduling, which
  is what this project shows.
- Astronomer's Astro CLI — a smoother local experience, but another vendor tool on top of the
  official image.

## Consequences
- Anyone with Docker and a GCP project runs the same pipeline: `make airflow-up ENV=…`.
- Nothing runs when the laptop is off — by design for a frozen dataset.
- Backfills are Airflow's own (`airflow backfill create`); only one backfill per DAG at a time, so a
  missed run is triggered by hand with its logical date.
