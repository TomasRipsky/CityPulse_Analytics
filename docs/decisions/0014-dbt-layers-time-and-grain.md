# 0014 — dbt in three layers, New York time, one grain per model

- **Status:** Accepted
- **Date:** 2026-10-05
- **Supersedes:** [0006](0006-dbt-staging-views-and-mart-tables.md)

## Context
Version 1's dbt project had staging views and four marts. Its only cross-source model was monthly
— five rows, all winter — and its "correlation" metrics divided trips by a Celsius temperature
(−331,730 in a month averaging −0.3 °C). Every target wrote to the same datasets, so CI tested
production tables, not the change.

## Decision
- **dbt-core 1.12** (supported to July 2027; 2.0, released September 2026, is too new to bet on).
- Three layers, each in its own dataset: **staging** (unit-named columns, New York time, trips
  de-duplicated across source files — views, except `stg_trips`, a table so the de-duplication
  runs once per build), **intermediate** (weather per hour with interval variables moved to the
  hour they describe; daily weather and air; trips per hour and per day as tables; calendar),
  **marts** (tables, including the baselines the effects are measured against).
- **Grains that can answer the question:** `fct_city_hour` (one row per hour) and
  `fct_city_day` (one row per New York day) join trips, weather, air quality and calendar.
  `mart_city_month` is a plain monthly summary for dashboards — totals and means, no ratios
  between unrelated units.
- **Time:** instants stay in UTC; days and hours are New York's (`date(ts, "America/New_York")`).
  Hourly keys are UTC hour starts: New York's offset is a whole number of hours, so they are also
  local hours, and the two 01:00s of the fall-back night stay apart.
- **"No data" ≠ "nobody rode":** trips are null for days whose month was never loaded and 0 for a
  day with no trips in a loaded month (which a test then flags).
- **Tests** at three levels: column tests (unique, not null, accepted values, ranges); dbt unit
  tests for the logic most likely to be wrong (dedupe, DST, interval shift, holidays, effect
  arithmetic); integrity tests driven by `raw.load_audit` (raw rows = audited rows = source rows;
  hours per New York day; trips every day). Failing rows are stored in the `audit` dataset.
- **CI** builds and tests each pull request's models in throwaway datasets on dev.

## Alternatives considered
- Keep the monthly join — cannot separate weather from season with a handful of rows.
- dbt 2.0 — new engine and project format; adapter maturity unknown a month after release.
- Incremental models — the dataset is frozen; full builds of the two trip tables cost a few GB.

## Consequences
- The analysis models read small tables (one row per hour or day), not 70 million trips.
- A full build reads the raw trips once (into `stg_trips`) and then only the columns each model
  or test needs: about 1.6 GiB on dev's sample, ~15 GB on prod's 16 months. The 20 GB per-query
  cap and the daily quota bound it.
