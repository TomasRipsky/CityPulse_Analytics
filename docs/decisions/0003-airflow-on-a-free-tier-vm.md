# 0003 — Airflow on a free-tier e2-micro VM, not Cloud Composer

- **Status:** Superseded by [0017](0017-airflow-3-from-a-versioned-image.md)
- **Date:** 2026-03-06 (recorded retroactively on 2026-10-04)

## Context
The pipeline needs a scheduler with dependencies, retries and a UI. Cloud Composer, the managed
Airflow on GCP, costs on the order of hundreds of euros a month even when idle — far beyond a
portfolio budget.

## Decision
Airflow 2.8.1 in standalone mode on a Compute Engine **e2-micro** (always-free tier in
`us-central1`), run by `systemd`, with 4 GB of swap because the machine has 1 GB of RAM. The VM
uses the project service account, so tasks reach GCS and BigQuery without keys. The UI is
reached through an SSH tunnel; the firewall only admits one IP.

## Alternatives considered
- Cloud Composer — managed and production-grade; rejected on cost.
- GitHub Actions cron — free, but no task graph, backfill UI or retries per task.
- Cloud Run jobs + Cloud Scheduler — cheap, but no orchestration model to learn.

## Consequences
- Zero compute cost while billing stays in the free tier.
- Everything is hand-installed (no image, no Terraform for Airflow itself), and code reaches
  the VM through `git pull` at task run time.
- Heavy tasks (a month of trips in pandas) live at the edge of 1 GB RAM.
