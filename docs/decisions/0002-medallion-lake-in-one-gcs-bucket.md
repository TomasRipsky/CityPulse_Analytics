# 0002 — Medallion lake in one GCS bucket, Hive-style paths

- **Status:** Accepted
- **Date:** 2026-03-06 (recorded 2026-10-04)

## Context
Raw API payloads and ZIPs must be kept exactly as received (so any later step can be replayed),
and a cleaned, typed copy must be cheap for BigQuery to load.

## Decision
One bucket (`city-pulse-tr`) with a prefix per layer:
- `bronze/` — the payload as received: JSON per day, the Citi Bike ZIP per month. Objects are
  deleted after 90 days by a lifecycle rule.
- `silver/` — typed Parquet (snappy), one file per day or month, timestamps cast to
  microseconds because BigQuery reads nanosecond Parquet timestamps as `INT64`.

Paths use Hive-style partitions: `<layer>/<source>/year=YYYY/month=MM/day=DD/<source>_YYYYMMDD.<ext>`.
Gold lives in BigQuery (0006). Uniform bucket-level access; no per-object ACLs.

## Alternatives considered
- One bucket per layer — more IAM and Terraform for no gain at this size.
- Loading JSON straight into BigQuery — couples the warehouse schema to the API response.

## Consequences
- Replays are cheap: Silver can be rebuilt from Bronze while Bronze is within its 90 days.
- After 90 days only Silver remains, so Silver must be correct — a processing bug older than
  90 days can only be fixed by re-extracting from the source.

## Revisited 2026-10-04
The layout is sound. The path convention, however, is rebuilt by hand in six modules (audit M2)
and the Terraform state lives in this same bucket (audit M4).
