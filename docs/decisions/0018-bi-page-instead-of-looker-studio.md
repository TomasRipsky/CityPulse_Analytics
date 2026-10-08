# 0018 — A BI page in the site instead of Looker Studio

- **Status:** Accepted
- **Date:** 2026-10-08

## Context
Version 1 listed a Looker Studio dashboard as done, with no link to it and no way to rebuild it:
Looker Studio reports are made in its web editor, and its only programmatic interface (the Linking
API) copies an existing report onto another data source — it cannot create or version charts. Its
look would also clash with the project's site. Version 2 still needs what a dashboard gives: a place
where a business reader filters the data and finds their own answers, next to the story that
explains the main one.

## Decision
- A second page of the Observable Framework site, `/bi`: filters (months, kind of day, rider, bike
  type), KPIs, demand, weather losses, a station map and ranking with a station panel, data quality,
  CSV downloads.
- **DuckDB-WASM in the browser** queries small Parquet files with SQL that reacts to the filters —
  no server, nothing queried in BigQuery when someone visits.
- The files come from report models in dbt (`rpt_*`, one stated grain each, reconciliation tests)
  exported by `citypulse site-export` and committed with the site, like the story page's CSVs.
- The per-period weather comparison moves into its own fact table (`fct_condition_periods`), so the
  effects and the monthly losses are two aggregations of the same rows.
- The old Looker Studio report and the version 1 GCP project behind it are gone.

## Alternatives considered
- Rebuild in Looker Studio — familiar to business users, but built by hand, not versioned, and
  every view queries BigQuery with the owner's credentials.
- Metabase, Superset, Lightdash — real BI servers, but always-on compute and upkeep for a frozen
  dataset.
- Evidence.dev — BI as code, a close fit, but a second site with a second look.

## Consequences
- €0 to run, versioned with the code, one look across the site; the page loads DuckDB-WASM
  (a few MB), only on `/bi`.
- No live data and no user accounts — acceptable for a frozen dataset; the page states its date.
- Filters work at the grain of the exported files: some charts filter by month rather than by day,
  and say so.
