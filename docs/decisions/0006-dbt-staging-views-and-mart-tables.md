# 0006 — dbt: staging views and mart tables in separate datasets

- **Status:** Superseded by [0014](0014-dbt-layers-time-and-grain.md)
- **Date:** 2026-03-07 (recorded retroactively on 2026-10-04)

## Context
The Gold layer must be tested, documented and cheap for a dashboard to query, while pipelines
keep writing raw tables.

## Decision
dbt Core on BigQuery with two layers:
- `staging` — one **view** per source in `citypulse_staging`, next to the raw tables: casts
  types, drops null keys, no business logic.
- `marts` — **tables** in `citypulse_marts`: three daily summaries and the monthly
  `monthly_city_pulse` that joins all three sources.

A `generate_schema_name` override makes `+schema` the dataset name as written
(`citypulse_marts`), instead of dbt's default `<target>_<schema>` concatenation. Quality:
26 generic tests (`not_null`, `unique`, `accepted_values`, a custom `between`) and 4 singular
tests (complete hours per day, member + casual = total, percentage range).

## Alternatives considered
- Python transformations in the loaders — no lineage, tests or docs.
- Views for marts — cheaper storage, but every dashboard query would recompute them.

## Consequences
- Lineage and docs come from `dbt docs`.
- The override means every target writes to the same datasets — dev, CI and prod share
  `citypulse_marts` unless the profile changes the project.
