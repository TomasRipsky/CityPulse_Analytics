---
title: When New York rides
---

# When does New York ride?

```js
import {fmt} from "./components/city.js";
const daily = FileAttachment("data/daily.csv").csv({typed: true});
const hourly = FileAttachment("data/hourly_profile.csv").csv({typed: true});
const months = FileAttachment("data/months.csv").csv({typed: true});
```

<div class="tip" label="What am I looking at?">

The city's rhythm: the shape of an average day (hour by hour, dry and wet), every day of the year as a calendar, and the months side by side. Hours are New York local time.

</div>

## Two rush hours on workdays, one long afternoon at weekends

```js
const profile = hourly.flatMap((d) => [
  {...d, weather: "dry hour", trips: d.dry_trips},
  {...d, weather: "wet hour (≥ 1 mm)", trips: d.wet_trips}
]).filter((d) => d.trips != null);
display(Plot.plot({
  height: 280,
  marginLeft: 56,
  x: {label: "hour of the day", ticks: [0, 6, 12, 18, 23]},
  y: {label: "average trips in the hour", grid: true, tickFormat: "s"},
  fx: {label: null},
  color: {domain: ["dry hour", "wet hour (≥ 1 mm)"], range: ["var(--series-1)", "var(--series-2)"], legend: true},
  marks: [
    Plot.lineY(profile, {fx: "day_type", x: "local_hour", y: "trips", stroke: "weather", strokeWidth: 2, curve: "monotone-x"}),
    Plot.tip(profile, Plot.pointerX({fx: "day_type", x: "local_hour", y: "trips", title: (d) => `${d.day_type}, ${d.local_hour}:00 · ${d.weather}\n${fmt.count(d.trips)} trips on average`}))
  ]
}))
```

On workdays the 8 a.m. and 5–6 p.m. peaks are commuters; rain flattens the evening peak more than the morning one, when people still have to get to work.

## The year, day by day

```js
const cal = daily.map((d) => ({...d, date: new Date(d.date)}));
display(Plot.plot({
  height: 190,
  marginLeft: 36,
  padding: 0.08,
  x: {label: null, tickFormat: () => ""},
  y: {label: null, domain: [1, 2, 3, 4, 5, 6, 0], tickFormat: (d) => "SMTWTFS"[d]},
  color: {type: "linear", scheme: "blues", label: "trips per day", legend: true, tickFormat: "s"},
  marks: [
    Plot.cell(cal, {x: (d) => d3.utcMonday.count(d3.utcMonday.floor(cal[0].date), d.date), y: (d) => d.date.getUTCDay(), fill: "trips", inset: 0.5, tip: true, title: (d) => `${fmt.date(d.date)} (${d.day_type})\n${fmt.count(d.trips)} trips · ${d.temperature_mean_c} °C · ${d.precipitation_mm} mm${d.snowfall_cm > 0 ? ` · ${d.snowfall_cm} cm snow` : ""}`})
  ]
}))
```

Each square is a day, darker when more people rode. Summer weekends glow; the pale columns are winter, and the white square in late February is the blizzard of 23 February 2026, when Citi Bike shut the whole system down.

## Month by month

<div class="grid grid-cols-2">
  <div class="card">${Plot.plot({
    title: "Trips per day",
    height: 220, marginLeft: 48,
    x: {label: null, type: "band", tickFormat: d3.utcFormat("%b")},
    y: {grid: true, tickFormat: "s", label: null},
    marks: [Plot.barY(months, {x: "month", y: "trips_per_day", fill: "var(--series-1)", insetLeft: 4, insetRight: 4, tip: true}), Plot.ruleY([0])]
  })}</div>
  <div class="card">${Plot.plot({
    title: "Mean temperature (°C)",
    height: 220, marginLeft: 40,
    x: {label: null, type: "band", tickFormat: d3.utcFormat("%b")},
    y: {grid: true, label: null},
    marks: [Plot.barY(months, {x: "month", y: "temperature_mean_c", fill: "var(--series-2)", insetLeft: 4, insetRight: 4, tip: true}), Plot.ruleY([0])]
  })}</div>
</div>

<div class="note">

Trips are counted by the New York day and hour they started. Trips under a minute (false starts) or over three hours (mostly bikes not docked properly) are left out.

</div>
