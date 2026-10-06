# 0013 — Atomic partition loads with a load audit

- **Status:** Accepted
- **Date:** 2026-10-05
- **Supersedes:** [0004](0004-idempotent-delete-then-append-loads.md)

## Context
Version 1 made loads idempotent with two statements: `DELETE` the day, then append the file. The
delete caught every exception and logged "no existing rows", so a delete that failed for any other
reason was followed by an append that duplicated the day. The tables were never partitioned, so
each delete scanned the whole table.

## Decision
- Raw tables are **partitioned by source period**, declared in Terraform with explicit schemas
  (`infra/gcp/schemas/`): `weather_hourly` and `air_quality_hourly` by New York day
  (`local_date`), `trips` by source file month (`source_month`).
- A period is loaded with **one** BigQuery load job into the **partition decorator**
  (`trips$202501`) with `WRITE_TRUNCATE`: it replaces that partition and nothing else, atomically.
  A failed job changes nothing.
- The schema comes from the table, never autodetected. A test compares the Silver (Arrow)
  schemas with the Terraform JSON schemas, so they cannot drift apart unnoticed.
- Only periods with a manifest are loaded, and only after the Parquet footers of its files add up
  to the manifest's row count — a mismatch stops before the table is touched. Each completed load
  appends a row to `raw.load_audit` (rows promised, rows written) and fails if they differ.
  `load_audit` is partitioned by month (`loaded_at`): an unpartitioned table accepts only 1,500
  changes a day.

## Alternatives considered
- `MERGE` on a key — more SQL, and hourly rows have no natural key.
- `WRITE_TRUNCATE` on the whole table — would wipe the history on every load.
- Autodetected schemas — a source change would silently change the warehouse.

## Consequences
- Re-running a period is always safe; a load job either replaces the whole partition or nothing.
  Doubtful files never replace a good partition, because they are checked first.
- Every row in the warehouse can be traced to a manifest, and every manifest to a load.
- Partitions bound the cost of queries that filter on the period.
