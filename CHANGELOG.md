# Changelog

All notable changes to CityPulse. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## [2.1.1] - 2026-10-09

### Fixed
- **The BI page broke in some browsers**: DuckDB-WASM read `daily.csv`'s quoted header into the
  column names, and since every table shares one database, every chart failed. The calendar is
  now Parquet like the rest, and a test keeps CSV out of the page's DuckDB tables.

## [2.1.0] - 2026-10-08

### Added
- **A BI page** (`/bi`): filters by month, kind of day, rider and bike; KPIs against the previous
  period; demand, weather losses, a station map, ranking and per-station panel, data quality, CSV
  download. DuckDB-WASM queries Parquet exports in the browser — no server, €0
  ([decision 0018](docs/decisions/0018-bi-page-instead-of-looker-studio.md)).
- Report models (`rpt_*`) with reconciliation tests, fed by one scan of the trips
  (`int_trip_hour_counts`); `fct_condition_periods` holds each period's expected vs actual trips.

### Removed
- The Looker Studio dashboard and the version 1 GCP project behind it.

## [2.0.2] - 2026-10-07

### Fixed
- **The site's logo scrolls back to the top**, and the section links no longer leave a heading
  under the sticky header (Framework's own `scroll-padding-top` was overriding ours).
- **The hero's trip count no longer wraps** onto two lines on mid-width screens.

## [2.0.1] - 2026-10-07

### Changed
- **The showcase site is one page with a New York personality**: a night skyline, rain and a bike
  on a green lane, the answers as street signs, the pipeline as a subway map and a case file on the
  23 February 2026 blizzard closure. Same data, same build and deploy
  ([site](https://tomasripsky.github.io/CityPulse_Analytics/)).

## [2.0.0] - 2026-10-06

A rebuild of the whole pipeline with tests, correct data and an answer to the project's question.

### Fixed
- **Every Citi Bike trip is loaded.** Each monthly archive holds several CSV files; version 1 read
  only the first one listed (40% of the trips). All of them are read now, and the rows are reconciled
  with the raw files at ingestion, at the BigQuery load and by a dbt test.
- **True UTC instants.** Version 1 stored New York wall-clock times as UTC (4–5 hours off). Days are
  now New York days, with 23 and 25 hours when the clocks change; rain is moved to the hour it fell in.
- **CI tests the change**, building each pull request's dbt models in throwaway datasets, instead of
  testing the production tables.
- **Loads cannot duplicate or half-write a period** (one partition replaced per job), and a failed
  re-run never destroys the last good data.
- **No identity can grant itself more rights**: one least-privilege service account, keyless CI.

### Changed
- One Python package and CLI (`citypulse`) instead of three folders of scripts; uv, ruff, pytest,
  pre-commit.
- Airflow 3.3 from a versioned image on the operator's machine, instead of Airflow 2.8 hand-installed
  on an always-on VM; dbt runs when new data lands (Airflow Assets).
- dbt 1.12 with hourly and daily cross-source facts and expected-vs-actual weather effects, instead
  of one monthly table of ratios.
- Two GCP projects (dev, prod) built entirely by Terraform, with budgets and query quotas.
- Bronze keeps a verifiable record of each trip archive instead of a 30-day copy of it.

### Added
- The answer: rain, snow, wind, air quality and temperature effects, for members and casual riders.
- A showcase site on GitHub Pages.
- The guide (`docs/guide.md`) and 17 decision records.

### Removed
- Version 1's `ingestion/`, `processing/`, `loading/`, `backfill.py`, Terraform and workflow.

## [1.0.0] - 2026-03-10

First version: Open-Meteo and Citi Bike → GCS → BigQuery → dbt → Looker Studio, orchestrated by
Airflow on a free-tier VM.

[2.0.0]: https://github.com/TomasRipsky/CityPulse_Analytics/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/TomasRipsky/CityPulse_Analytics/tree/v1.0.0
