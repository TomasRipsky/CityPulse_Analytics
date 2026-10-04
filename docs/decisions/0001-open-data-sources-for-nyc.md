# 0001 — Open-Meteo and Citi Bike open data for New York

- **Status:** Accepted
- **Date:** 2026-03-06 (recorded retroactively on 2026-10-04)

## Context
The project asks one question: **how do weather and air quality affect bike-share use in a
city?** It needs a weather source, an air-quality source and a mobility source for the same
place, all free, with history for backfills and no credentials to manage.

## Decision
New York City, with three open sources:
- **Open-Meteo Forecast / Archive API** — hourly temperature, precipitation, wind and humidity.
  No API key. The archive endpoint covers any past date; the forecast endpoint covers recent days.
- **Open-Meteo Air Quality API** — hourly PM2.5, PM10, ozone and US AQI. No API key.
- **Citi Bike System Data** (`s3://tripdata`, public HTTPS) — one ZIP of trip CSVs per month,
  published about six weeks after the month ends.

## Alternatives considered
- NYC Open Data weather/air feeds — fragmented, inconsistent schemas.
- Real-time GBFS station feeds — station availability, not trips; needs always-on polling.
- Another city's bike share — NYC has the largest, longest-running open trip dataset in the US.

## Consequences
- Two cadences: weather and air quality are daily; trips are monthly and late (see 0007).
- Licences: Open-Meteo data is CC BY 4.0 (attribute and link "Weather data by Open-Meteo.com").
  Citi Bike data may be used in non-commercial analyses but not republished as a stand-alone
  dataset; we publish aggregates only and claim no affiliation.
