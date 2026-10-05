# 0015 — Weather effects as expected vs actual trips

- **Status:** Accepted
- **Date:** 2026-10-05

## Context
"How does the weather change bike use?" has an obvious trap: bad weather comes with seasons, and
seasons come with daylight, holidays and tourists. Summer has more trips *and* more thunderstorms;
comparing rainy days with dry days across the year mixes the two. The answer also has to be
explainable on a public page to people who know no statistics.

## Decision
Measure each condition against what the same kind of period gets in good weather:

- **Expected trips** = the mean trips of the condition's **reference periods** — good conditions
  of its own kind — with the same month, the same kind of day (workday or weekend; holidays count
  as weekends, a month has too few for their own baseline) and, for rain, the same hour of the day
  (`mart_baselines`, at least 3 reference periods per cell). References: dry hours (rain), dry days
  (snow), dry days with gusts under 40 km/h (wind), dry days with good air (air quality).
- **Effect** = actual ÷ expected − 1, summed over every period in a band
  (`mart_condition_effects`), for all riders, members and casual riders separately. The reference
  band is listed too (`is_reference`); its effect is ~0 by construction, a built-in check.
- **Rain** is measured per **hour** (showers come and go; a day with one wet hour is not a rainy
  day); **snow, wind and air quality** per **day**, wind and air on otherwise dry days.
- A band is never compared with a baseline that contains its own periods: with "all dry days" as
  the baseline for wind, the calm and windy bands would split the baseline between them, their
  effects would have to add up to zero, calm days would show an effect they do not have and windy
  ones would be understated (a code review caught this before any number was published).
- **Temperature** has two views: the raw curve of trips per dry day by felt temperature
  (`mart_temperature_curve`, honest about mixing in the season), and the response with the
  season held still — each dry day against its own month's mean — as "% more trips per °C
  warmer than usual" (`mart_temperature_response`, a least-squares slope).

## Alternatives considered
- A regression with every variable at once (e.g. BigQuery ML) — one model, but its coefficients
  are hard to explain and easy to over-read.
- Correlation over the whole period — dominated by the seasonal cycle.

## Consequences
- Each number reads as a sentence: "an hour of rain (1–4 mm) has N% fewer trips than the same hour
  on a dry day of the same month".
- Bands with few periods are noisy; the site shows the number of periods next to every effect.
- The method holds month and kind of day still, not everything: a stormy hour may also be darker,
  colder or a commute hour. These are associations measured carefully, not proof of cause.
