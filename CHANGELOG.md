# Changelog

All notable changes to CityPulse. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

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
