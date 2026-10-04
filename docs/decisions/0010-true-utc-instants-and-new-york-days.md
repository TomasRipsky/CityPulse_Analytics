# 0010 — True UTC instants and New York calendar days

- **Status:** Accepted
- **Date:** 2026-10-04

## Context
Version 1 asked Open-Meteo for `timezone=America/New_York` and parsed the answers, local
wall-clock times without an offset, as UTC. Citi Bike times, also local, got the same treatment.
Every timestamp was off by four or five hours. Daily totals looked right only because every
source was shifted the same way. Checking the API showed a second trap: with a local timezone,
Open-Meteo returns 24 hours at **one fixed offset** even on the two days a year when New York
changes its clocks.

## Decision
- **Weather and air quality:** request `timezone=GMT`, `timeformat=unixtime` (epoch seconds) for
  the two UTC dates that a New York day spans, and keep the hours whose New York date is the
  requested day: 24 normally, **23** on the spring-forward Sunday, **25** on the fall-back Sunday.
- **Trips:** read the local times and convert them with the IANA zone `America/New_York`
  (`pyarrow.compute.assume_timezone`). On the fall-back night the repeated hour is read as its
  first occurrence (daylight time); a reading inside the spring-forward gap becomes 03:00
  daylight time.
- Silver stores instants as `timestamp[us, tz=UTC]`; daily sources also carry `local_date`, the
  New York day. Daily and hourly models group by the New York calendar, never by the UTC date.

## Alternatives considered
- Trust the API's local day — wrong on daylight-saving days.
- Keep everything in local time (`DATETIME`) — ambiguous one hour a year and impossible to join
  with sources in other zones.

## Consequences
- Every timestamp is an unambiguous instant; dashboards convert to local time for display.
- A day can have 23, 24 or 25 hours: completeness checks use the real length of the day.
- One hour per year of trips (the repeated hour) is assigned to its first occurrence — documented
  and negligible.
