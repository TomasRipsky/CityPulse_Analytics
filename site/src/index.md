---
title: CityPulse
toc: false
---

```js
import {colors, effect, fmt} from "./components/city.js";
const daily = FileAttachment("data/daily.csv").csv({typed: true});
const effects = FileAttachment("data/effects.csv").csv({typed: true});
const response = FileAttachment("data/temperature_response.csv").csv({typed: true});
const summary = FileAttachment("data/summary.json").json();
```

```js
const days = daily.map((d) => ({...d, date: new Date(d.date)}));
const busiest = d3.greatest(days, (d) => d.trips);
const blizzard = days.find((d) => d.trips === 0);
const rain = effect(effects, "rain", "rain (1–4 mm/h)");
const snow = effect(effects, "snow", "snowfall ≥ 5 cm");
const air = effect(effects, "air quality", "moderate");
const warmth = response.find((d) => d.rider === "all");
```

<div class="hero">
  <p class="kicker">New York City · May 2025 – April 2026</p>
  <h1>Does the weather change how New York rides bikes?</h1>
  <p class="lede">${fmt.millions(summary.trips)} Citi Bike trips and every hour of the city's weather and air quality for a year — one line per day below. This is the city's pulse.</p>
</div>

```js
display(Plot.plot({
  height: 240,
  marginLeft: 48,
  x: {label: null},
  y: {label: "trips per day", grid: true, tickFormat: "s"},
  marks: [
    Plot.areaY(days, {x: "date", y: "trips", fill: "var(--series-1)", fillOpacity: 0.1, curve: "monotone-x"}),
    Plot.lineY(days, {x: "date", y: "trips", stroke: "var(--series-1)", strokeWidth: 1.5, curve: "monotone-x"}),
    Plot.dot([busiest, blizzard], {x: "date", y: "trips", r: 4, fill: "var(--series-1)", stroke: "var(--theme-background)", strokeWidth: 2}),
    Plot.text([busiest], {x: "date", y: "trips", text: (d) => `busiest day: ${fmt.count(d.trips)}`, dy: -12, textAnchor: "middle"}),
    Plot.ruleX([blizzard], {x: "date", y1: 0, y2: 55000, stroke: "var(--theme-foreground-muted)"}),
    Plot.text([blizzard], {x: "date", y: 60000, text: () => "23 Feb 2026: blizzard, system shut", textAnchor: "end", dx: -4}),
    Plot.tip(days, Plot.pointerX({x: "date", y: "trips", title: (d) => `${fmt.date(d.date)}\n${fmt.count(d.trips)} trips\n${d.temperature_mean_c} °C · ${d.precipitation_mm} mm`}))
  ]
}))
```

<div class="answers">
  <div class="answer"><div class="value">${fmt.signedPct(rain.effect_pct)}</div><div class="label">trips in an hour of rain (1–4 mm) than in the same hour when it is dry</div></div>
  <div class="answer"><div class="value">${fmt.signedPct(snow.effect_pct)}</div><div class="label">trips on a day with 5 cm of snow or more</div></div>
  <div class="answer warm"><div class="value">+${warmth.pct_per_degree.toFixed(1)}%</div><div class="label">trips for every °C a day is warmer than usual for its month</div></div>
  <div class="answer"><div class="value">${fmt.signedPct(air.effect_pct)}</div><div class="label">on a "moderate" air-quality day: bad air does not keep riders home</div></div>
</div>

<div class="tip" label="What am I looking at?">

Each answer compares like with like: an hour of rain with **the same hour of the same kind of day in the same month when it was dry** — so the season, the weekday and the rush hour are held still. [How the effects are measured →](./weather)

</div>

## Explore

- [**What the weather does**](./weather) — rain, snow, wind, air quality and temperature, for members and casual riders.
- [**When New York rides**](./rhythm) — the daily rush hours, the weekend, the calendar of a whole year.
- [**How it is built**](./built) — a tested pipeline from three public sources to these pages.

<div class="note">

One year of data (${summary.first_day} to ${summary.last_day}). These are careful associations, not proof of cause: a rainy hour may also be darker or colder. Counts exclude trips under a minute or over three hours.

</div>
