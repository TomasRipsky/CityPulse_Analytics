# 0004 — Idempotent loads: delete the period, then append

- **Status:** Accepted
- **Date:** 2026-03-07 (recorded 2026-10-04)

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

## Revisited 2026-10-04
The intent is right; the implementation is not safe. The delete swallows every exception and
logs "no existing rows", so a failed delete is followed by an append that duplicates the day
(audit H3). The tables were also never partitioned, so each delete scans the whole table.
A partition-decorator `WRITE_TRUNCATE` (`table$YYYYMMDD`) on a partitioned table does the same
job atomically, in one statement.
