---
title: What the weather does
---

# What does the weather do to a bike ride?

```js
import {colors, riderLabel, riders, fmt} from "./components/city.js";
const effects = FileAttachment("data/effects.csv").csv({typed: true});
const curve = FileAttachment("data/temperature_curve.csv").csv({typed: true});
const response = FileAttachment("data/temperature_response.csv").csv({typed: true});
```

<div class="tip" label="What am I looking at?">

For every hour (rain) or day (snow, wind, air quality), CityPulse asks: **how many trips would this have had in good conditions?** — the average of dry periods with the same month, the same kind of day and, for rain, the same hour. The bars show how far the real count fell below (or rose above) that. 0% is "no difference". Members are annual subscribers, mostly commuting; casual riders buy single rides or day passes.

</div>

```js
// One row per band; a dot per rider, joined by a line: the spread between commuters and casual riders.
function effectChart(condition) {
  const rows = effects.filter((d) => d.condition === condition && !d.is_reference);
  const bands = [...new Set([...rows].sort((a, b) => a.band_order - b.band_order).map((d) => d.band))];
  const span = d3.rollups(rows, (v) => d3.extent(v, (d) => d.effect_pct), (d) => d.band).map(([band, [lo, hi]]) => ({band, lo, hi}));
  return Plot.plot({
    height: 40 + bands.length * 44,
    marginLeft: 190,
    marginRight: 40,
    x: {label: "trips vs good conditions (%)", grid: true, tickFormat: (d) => `${d > 0 ? "+" : ""}${d}`},
    y: {label: null, domain: bands},
    color: {domain: riders, range: riders.map((r) => colors[r]), legend: true, tickFormat: (r) => riderLabel[r]},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.ruleY(span, {y: "band", x1: "lo", x2: "hi", stroke: "var(--theme-foreground-faint)", strokeWidth: 2}),
      Plot.dot(rows, {y: "band", x: "effect_pct", fill: "rider", r: 6, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.text(rows.filter((d) => d.rider === "all"), {y: "band", x: "effect_pct", text: (d) => fmt.signedPct(d.effect_pct), dy: -13, fill: "var(--theme-foreground-muted)"}),
      Plot.tip(rows, Plot.pointer({y: "band", x: "effect_pct", title: (d) => `${d.band} · ${riderLabel[d.rider]}\n${fmt.signedPct(d.effect_pct)}: ${fmt.count(d.trips)} trips vs ${fmt.count(d.expected_trips)} expected\n${d.periods} ${condition === "rain" ? "hours" : "days"}`}))
    ]
  });
}
```

## Rain empties the streets — by the hour

```js
display(effectChart("rain"))
```

A drizzle is already enough to lose a quarter of the riders; steady rain halves them. Casual riders react more than commuters, who still have to get to work. (Heavy-rain hours are few — the count is in the tooltip.)

## Snow, wind and air quality

<div class="card"><h3>Snow (per day)</h3>${effectChart("snow")}</div>
<div class="card"><h3>Wind (dry days)</h3>${effectChart("wind")}</div>
<div class="card"><h3>Air quality (dry days)</h3>${effectChart("air quality")}</div>

Snow is the strongest weather effect of all (heavy-snow days are few — counts in the tooltips). Wind, surprisingly, barely matters. And "moderate" air quality does not keep riders home: those are often the warm, sunny days when ozone builds up, so warmth is mixed into this comparison.

## Warmer days, more riders

```js
const all = response.find((d) => d.rider === "all");
const member = response.find((d) => d.rider === "member");
const casual = response.find((d) => d.rider === "casual");
```

<div class="answers">
  <div class="answer warm"><div class="value">+${all.pct_per_degree.toFixed(1)}%</div><div class="label">trips per °C of felt temperature above the month's usual, on dry days — all riders</div></div>
  <div class="answer"><div class="value">+${member.pct_per_degree.toFixed(1)}%</div><div class="label">members</div></div>
  <div class="answer warm"><div class="value">+${casual.pct_per_degree.toFixed(1)}%</div><div class="label">casual riders: the most sensitive to warmth</div></div>
</div>

```js
display(Plot.plot({
  height: 300,
  marginLeft: 56,
  x: {label: "felt temperature, daily mean (°C)", grid: true},
  y: {label: "trips per dry day", grid: true, tickFormat: "s", zero: true},
  color: {domain: ["workday", "weekend"], range: ["var(--series-1)", "var(--series-2)"], legend: true},
  marks: [
    Plot.lineY(curve, {x: (d) => (d.band_from_c + d.band_to_c) / 2, y: "trips_per_day", stroke: "day_type", strokeWidth: 2, curve: "monotone-x"}),
    Plot.dot(curve, {x: (d) => (d.band_from_c + d.band_to_c) / 2, y: "trips_per_day", fill: "day_type", r: 4, stroke: "var(--theme-background)", strokeWidth: 2, tip: true, title: (d) => `${d.band_from_c} to ${d.band_to_c} °C · ${d.day_type}\n${fmt.count(d.trips_per_day)} trips per day (${d.days} days)\ncasual share ${d.casual_share_pct}%`})
  ]
}))
```

The curve is the whole season at once — warm months also bring longer days, holidays and tourists. The numbers above hold the season still: each day is compared with its own month.

<div class="note">

Associations, not proof of cause. Bands with few periods are noisy (counts in the tooltips). Expected values need at least three good-weather periods of the same kind; holidays are compared with weekends.

</div>
