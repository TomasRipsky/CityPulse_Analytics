# 0011 — Trips de-duplicated in staging, not filtered by month

- **Status:** Accepted (implemented in `stg_trips`)
- **Date:** 2026-10-04

## Context
A monthly trip file can contain trips that started on the last evening of the previous month.
Version 1 dropped every trip whose start month differed from the file's month, in a `where`
clause nobody would notice. If those trips are not also in the previous file, they are lost; if
they are, the filter hides a duplicate instead of handling it.

## Decision
Raw trips keep every row of every file, with `source_month` and `source_file`. The staging model
de-duplicates on `ride_id` (keeping the row from the latest source month), and a test asserts
`ride_id` is unique after staging. Daily models assign trips to the New York day they started.

## Alternatives considered
- Filter by month — silent loss or silent duplicate, depending on the publisher.
- De-duplicate in Python — the warehouse sees all months at once and does it in one query.

## Consequences
- No trip is lost at a month boundary, and duplicates are explicit and counted.
- The raw table is a faithful copy of the files, so its row counts reconcile with the manifests.
