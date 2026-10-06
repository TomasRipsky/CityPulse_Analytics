# 0004 — Idempotent loads: delete the period, then append

- **Status:** Superseded by [0013](0013-atomic-partition-loads-with-audit.md)
- **Date:** 2026-03-07 (recorded retroactively on 2026-10-04)

## Context
Airflow retries tasks and backfills re-run past dates. Loading the same day twice must not
duplicate rows in BigQuery.

## Decision
Each loader first deletes the period it is about to load — `where date = <day>` for weather and
air quality, `where year = <y> and month = <m>` for Citi Bike — then appends the Silver Parquet
file with a BigQuery load job (`WRITE_APPEND`, schema autodetected).

## Alternatives considered
- `WRITE_TRUNCATE` on the whole table — would wipe the history on every daily load.
- `MERGE` on a key — more SQL; no natural key for hourly rows at the time.

## Consequences
- Re-running a day replaces that day.
- Two statements, not one: if the load fails after the delete, the day is missing until the
  next successful run.
