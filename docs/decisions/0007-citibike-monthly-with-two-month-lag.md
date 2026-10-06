# 0007 — Citi Bike loaded monthly, two months behind

- **Status:** Accepted
- **Date:** 2026-03-09 (recorded retroactively on 2026-10-04)

## Context
Citi Bike publishes a month of trips roughly six weeks after it ends, on no fixed day. A
monthly job that asks for "last month" fails because the file is not there yet.

## Decision
A separate monthly DAG runs on the 8th at 06:00 UTC and loads the month **two** months before
the run (a run on 8 May loads March). The daily DAG handles weather and air quality; both
finish with `dbt run`.

## Alternatives considered
- A sensor polling S3 until the file appears — more moving parts on a 1 GB VM.
- One DAG for everything — would tie the daily sources to a monthly, late source.

## Consequences
- Trips are always at least ~5 weeks behind weather; marts that join them are only complete
  for months older than that.
- If the file is still missing on the 8th, the run fails and needs a manual re-run.

The lag survives in version 2 (`citypulse_monthly`, decision 0017), run on the 15th instead of the 8th.
