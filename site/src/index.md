---
title: Does the weather change how New York rides bikes?
---

```js
import {colors, effect, fmt, riderLabel, riders} from "./components/city.js";
import {particles, skyline} from "./components/street.js";
const daily = FileAttachment("data/daily.csv").csv({typed: true});
const effects = FileAttachment("data/effects.csv").csv({typed: true});
const curve = FileAttachment("data/temperature_curve.csv").csv({typed: true});
const response = FileAttachment("data/temperature_response.csv").csv({typed: true});
const hourly = FileAttachment("data/hourly_profile.csv").csv({typed: true});
const months = FileAttachment("data/months.csv").csv({typed: true});
const summary = FileAttachment("data/summary.json").json();
```

```js
const days = daily.map((d) => ({...d, date: new Date(d.date)}));
const busiest = d3.greatest(days, (d) => d.trips);
const blizzard = days.find((d) => d.trips === 0);
const pick = (condition, band) => Object.fromEntries(riders.map((r) => [r, effect(effects, condition, band, r)]));
const drizzle = pick("rain", "drizzle (< 1 mm/h)");
const rain = pick("rain", "rain (1–4 mm/h)");
const snow = pick("snow", "snowfall ≥ 5 cm");
const wind = pick("wind", "windy (55–70 km/h)");
const air = pick("air quality", "moderate");
const warmth = Object.fromEntries(response.map((d) => [d.rider, d]));
const split = (e) => html`<div class="split"><span class="swatch member"></span>members ${fmt.signedPct(e.member.effect_pct)} · <span class="swatch casual"></span>casual ${fmt.signedPct(e.casual.effect_pct)}</div>`;
```

```js
// Charts: functions of the panel width, drawn through resize().
function pulse(width) {
  return Plot.plot({
    width, height: 260, marginLeft: 48, marginTop: 28,
    x: {label: null},
    y: {label: "trips per day", grid: true, tickFormat: "s"},
    marks: [
      Plot.areaY(days, {x: "date", y: "trips", fill: "var(--series-1)", fillOpacity: 0.14, curve: "monotone-x"}),
      Plot.lineY(days, {x: "date", y: "trips", stroke: "var(--series-1)", strokeWidth: 2, curve: "monotone-x"}),
      Plot.dot([busiest, blizzard], {x: "date", y: "trips", r: 5, fill: "var(--taxi)", stroke: "var(--night)", strokeWidth: 2}),
      Plot.text([busiest], {x: "date", y: "trips", text: (d) => `busiest day: ${fmt.count(d.trips)}`, dy: -14, fill: "var(--ink)"}),
      Plot.ruleX([blizzard], {x: "date", y1: 0, y2: 60000, stroke: "var(--taxi)", strokeDasharray: "3 3"}),
      Plot.text([blizzard], {x: "date", y: 66000, text: () => "23 Feb: blizzard, system shut", textAnchor: "end", dx: 6, fill: "var(--taxi)"}),
      Plot.tip(days, Plot.pointerX({x: "date", y: "trips", title: (d) => `${fmt.date(d.date)} (${d.day_type})\n${fmt.count(d.trips)} trips\n${d.temperature_mean_c} °C · ${d.precipitation_mm} mm${d.snowfall_cm > 0 ? ` · ${d.snowfall_cm} cm snow` : ""}`}))
    ]
  });
}

// One row per band, a dot per rider joined by a line: the spread between commuters and casual riders.
function effectChart(condition, width) {
  const rows = effects.filter((d) => d.condition === condition && !d.is_reference);
  const bands = [...new Set([...rows].sort((a, b) => a.band_order - b.band_order).map((d) => d.band))];
  const span = d3.rollups(rows, (v) => d3.extent(v, (d) => d.effect_pct), (d) => d.band).map(([band, [lo, hi]]) => ({band, lo, hi}));
  const narrow = width < 520;
  return Plot.plot({
    width, height: 50 + bands.length * (narrow ? 56 : 46),
    marginLeft: narrow ? 10 : 190, marginRight: 30, marginTop: narrow ? 26 : 20,
    x: {label: "trips vs good conditions (%)", grid: true, tickFormat: (d) => `${d > 0 ? "+" : ""}${d}`},
    y: {label: null, domain: bands, axis: narrow ? null : "left"},
    color: {domain: riders, range: riders.map((r) => colors[r]), legend: true, tickFormat: (r) => riderLabel[r]},
    marks: [
      Plot.ruleX([0], {stroke: "var(--mist)", strokeOpacity: 0.6}),
      // narrow screens: the band's name and its all-riders value on one line above the dots
      narrow ? Plot.text(rows.filter((d) => d.rider === "all"), {y: "band", frameAnchor: "left", dy: -17, text: (d) => `${d.band}: ${fmt.signedPct(d.effect_pct)}`, fill: "var(--mist)"}) : null,
      Plot.ruleY(span, {y: "band", x1: "lo", x2: "hi", stroke: "var(--curb)", strokeWidth: 3}),
      Plot.dot(rows, {y: "band", x: "effect_pct", fill: "rider", r: 6.5, stroke: "var(--night)", strokeWidth: 2}),
      narrow ? null : Plot.text(rows.filter((d) => d.rider === "all"), {y: "band", x: "effect_pct", text: (d) => fmt.signedPct(d.effect_pct), dy: -14, fill: "var(--ink)"}),
      Plot.tip(rows, Plot.pointer({y: "band", x: "effect_pct", title: (d) => `${d.band} · ${riderLabel[d.rider]}\n${fmt.signedPct(d.effect_pct)}: ${fmt.count(d.trips)} trips vs ${fmt.count(d.expected_trips)} expected\n${d.periods} ${condition === "rain" ? "hours" : "days"}`}))
    ]
  });
}

// Dry vs wet hours: identity by colour, a legend and a direct label at each peak.
const profile = hourly.flatMap((d) => [
  {...d, weather: "dry hour", trips: d.dry_trips},
  {...d, weather: "wet hour (≥ 1 mm)", trips: d.wet_trips}
]).filter((d) => d.trips != null);
function rush(width) {
  return Plot.plot({
    width, height: 290, marginLeft: 50,
    x: {label: "hour of the day (New York)", ticks: [0, 6, 8, 12, 17, 23]},
    y: {label: "average trips in the hour", grid: true, tickFormat: "s"},
    fx: {label: null},
    color: {domain: ["dry hour", "wet hour (≥ 1 mm)"], range: ["var(--ink)", "var(--rain)"], legend: true},
    marks: [
      Plot.lineY(profile, {fx: "day_type", x: "local_hour", y: "trips", stroke: "weather", strokeWidth: 2, curve: "monotone-x"}),
      Plot.text(profile, Plot.selectMaxY({fx: "day_type", x: "local_hour", y: "trips", z: "weather", text: (d) => d.weather.split(" (")[0], dy: -10, fill: "var(--mist)"})),
      Plot.tip(profile, Plot.pointerX({fx: "day_type", x: "local_hour", y: "trips", title: (d) => `${d.day_type}, ${d.local_hour}:00 · ${d.weather}\n${fmt.count(d.trips)} trips on average`}))
    ]
  });
}

function warmCurve(width) {
  const mid = (d) => (d.band_from_c + d.band_to_c) / 2;
  return Plot.plot({
    width, height: 300, marginLeft: 50, marginRight: 70,
    x: {label: "felt temperature, daily mean (°C)", grid: true},
    y: {label: "trips per dry day", grid: true, tickFormat: "s", zero: true},
    color: {domain: ["workday", "weekend"], range: ["var(--ink)", "var(--taxi)"], legend: true},
    marks: [
      Plot.lineY(curve, {x: mid, y: "trips_per_day", stroke: "day_type", strokeWidth: 2, curve: "monotone-x"}),
      Plot.text(curve, Plot.selectLast({x: mid, y: "trips_per_day", z: "day_type", text: "day_type", dx: 10, textAnchor: "start", fill: "var(--mist)"})),
      Plot.dot(curve, {x: mid, y: "trips_per_day", fill: "day_type", r: 4.5, stroke: "var(--night)", strokeWidth: 2, tip: true, title: (d) => `${d.band_from_c} to ${d.band_to_c} °C · ${d.day_type}\n${fmt.count(d.trips_per_day)} trips per day (${d.days} days)\ncasual share ${d.casual_share_pct}%`})
    ]
  });
}

// The year as a calendar: one hue, dark (few trips) to bright (many) on the night surface.
function calendar(width) {
  const start = d3.utcMonday.floor(days[0].date);
  const monthStarts = new Map(d3.utcMonth.range(days[0].date, days.at(-1).date).map((m) => [d3.utcMonday.count(start, m), d3.utcFormat("%b")(m)]));
  return Plot.plot({
    width, height: 200, marginLeft: 26, marginBottom: 26, padding: 0.1,
    x: {label: null, ticks: [...monthStarts.keys()], tickFormat: (w) => monthStarts.get(w)},
    y: {label: null, domain: [1, 2, 3, 4, 5, 6, 0], tickFormat: (d) => "SMTWTFS"[d]},
    color: {type: "linear", range: ["#162238", "#8cc0ff"], label: "trips per day", legend: true, tickFormat: "s"},
    marks: [
      Plot.cell(days, {x: (d) => d3.utcMonday.count(start, d.date), y: (d) => d.date.getUTCDay(), fill: "trips", inset: 0.5, rx: 2, tip: true, title: (d) => `${fmt.date(d.date)} (${d.day_type})\n${fmt.count(d.trips)} trips · ${d.temperature_mean_c} °C · ${d.precipitation_mm} mm${d.snowfall_cm > 0 ? ` · ${d.snowfall_cm} cm snow` : ""}`}),
      Plot.cell([blizzard], {x: (d) => d3.utcMonday.count(start, d.date), y: (d) => d.date.getUTCDay(), stroke: "var(--taxi)", strokeWidth: 2, inset: 0.5, rx: 2})
    ]
  });
}

function monthBars(width, y, fill, label) {
  return Plot.plot({
    width, height: 220, marginLeft: 44,
    x: {label: null, type: "band", tickFormat: (m) => d3.utcFormat("%b")(new Date(m)).slice(0, width < 480 ? 1 : 3)},
    y: {grid: true, tickFormat: "s", label},
    marks: [Plot.barY(months, {x: "month", y, fill, insetLeft: 3, insetRight: 3, rx: 4, tip: true}), Plot.ruleY([0], {stroke: "var(--mist)"})]
  });
}

// The case file: the fortnight around the blizzard, and the hours Citi Bike was closed.
const storm = days.filter((d) => d.date >= new Date("2026-02-17") && d.date <= new Date("2026-03-01"));
function stormChart(width) {
  return Plot.plot({
    width, height: 300, marginLeft: 46, marginTop: 30,
    x: {label: null, type: "utc", tickFormat: "%-d %b", ticks: d3.utcDay.every(2)},
    y: {label: "trips per day", grid: true, tickFormat: "s"},
    marks: [
      Plot.rectY([{x1: new Date("2026-02-22T20:00Z"), x2: new Date("2026-02-24T00:00Z")}], {x1: "x1", x2: "x2", y1: 0, y2: 84000, fill: "var(--taxi)", fillOpacity: 0.12}),
      Plot.text(["system closed"], {x: new Date("2026-02-23T10:00Z"), y: 80000, text: (d) => d, fill: "var(--taxi)", fontWeight: 700}),
      Plot.rectY(storm, {x1: "date", x2: (d) => d3.utcDay.offset(d.date), y: "trips", fill: "var(--series-1)", insetLeft: 4, insetRight: 4, rx: 4, tip: true, title: (d) => `${fmt.date(d.date)}\n${fmt.count(d.trips)} trips · ${d.snowfall_cm} cm snow · ${d.temperature_mean_c} °C`}),
      Plot.text(storm.filter((d) => d.snowfall_cm > 0), {x: (d) => d3.utcHour.offset(d.date, 12), y: "trips", text: (d) => `❄ ${d.snowfall_cm} cm`, dy: -10, fill: "var(--ink)"}),
      Plot.ruleY([0], {stroke: "var(--mist)"})
    ]
  });
}
```

<header class="top" id="top">
  <a class="brand" href="#top" aria-label="CityPulse, back to the top">
    <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="5.5"/><circle cx="24" cy="21" r="5.5"/><path d="M8 21l5-9h8l3 9M13 12l-1.6-3H9.5M21 12l1-3h2.5M16 21l-3-9"/></g></svg>
    CityPulse
  </a>
  <nav aria-label="Sections">
    <a href="#answer">The answer</a>
    <a href="#rain">Rain</a>
    <a href="#weather">Snow & wind</a>
    <a href="#warmth">Warmth</a>
    <a href="#rhythm">Rhythm</a>
    <a href="#blizzard">The blizzard</a>
    <a href="#pipeline">Pipeline</a>
    <a href="#decisions">Decisions</a>
    <a href="#quality">Quality</a>
    <a class="gh" href="https://github.com/TomasRipsky/CityPulse_Analytics">GitHub ↗</a>
  </nav>
</header>

<section class="hero">
  ${particles(70, "rain", 11, [0.6, 1.4])}
  <div class="hero-copy">
    <p class="eyebrow">New York City · Citi Bike · May 2025 – April 2026</p>
    <h1>Does the weather change how <em>New York</em> rides bikes?</h1>
    <p class="lede">CityPulse lands every Citi Bike trip and every hour of the city's weather and air quality in Google Cloud, proves nothing was lost on the way, and compares each rainy hour with the same hour when it was dry. One year, one city, one question — answered.</p>
    <div class="stats">
      <div class="stat"><b>${fmt.count(summary.trips)}</b><span>trips analysed</span></div>
      <div class="stat"><b>${summary.days}</b><span>New York days</span></div>
      <div class="stat"><b>${fmt.count(summary.days * 24)}</b><span>hours of weather and air quality</span></div>
      <div class="stat"><b>153</b><span>automated checks</span></div>
    </div>
  </div>
  ${skyline()}
</section>

<div class="street" aria-hidden="true">
  ${[8, 30, 52, 74, 96].map((x) => html`<svg class="stencil" style="left:${x}%" viewBox="0 0 48 28"><g fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="10" cy="18" r="7"/><circle cx="38" cy="18" r="7"/><path d="M10 18l8-11h12l8 11M18 7l6 11M30 7l2-4"/></g></svg>`)}
  <svg class="rider" viewBox="0 0 74 70"><g fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><g class="wheel"><circle cx="15" cy="54" r="13"/><path d="M15 41v26M2 54h26"/></g><g class="wheel"><circle cx="59" cy="54" r="13"/><path d="M59 41v26M46 54h26"/></g><path d="M15 54l13-20h22l9 20M28 34l9 20h13M50 34l2-6h6"/><path d="M37 54l-4-24 12-8 6 12" stroke="#f5c518"/><circle cx="44" cy="12" r="5" fill="currentColor" stroke="none"/><path d="M33 9h14" stroke="#f5c518" stroke-width="4"/></g></svg>
</div>

<section id="answer" class="band">
<div class="wrap">
  <h2><span class="bullet yellow">A</span>The answer, block by block</h2>
  <p class="sub">Each number compares like with like: an hour of rain against <b>the same hour, on the same kind of day, in the same month, when it was dry</b> — so neither the season nor the rush hour can pass for weather.</p>
  <div class="signs">
    <div class="sign"><span class="plate">Drizzle St</span><b>${fmt.signedPct(drizzle.all.effect_pct)}</b><p>trips in an hour of drizzle (under 1 mm). A quarter of the riders stay off the bike.</p>${split(drizzle)}</div>
    <div class="sign"><span class="plate">Rain Ave</span><b>${fmt.signedPct(rain.all.effect_pct)}</b><p>trips in an hour of steady rain (1–4 mm). Half the city takes the subway instead.</p>${split(rain)}</div>
    <div class="sign"><span class="plate">Snow Blvd</span><b>${fmt.signedPct(snow.all.effect_pct)}</b><p>trips on a day with 5 cm of snow or more (${snow.all.periods} days) — the strongest effect of all.</p>${split(snow)}</div>
    <div class="sign"><span class="plate">Warmth Dr</span><b>+${warmth.all.pct_per_degree.toFixed(1)}%<small> /°C</small></b><p>trips for every degree a dry day feels warmer than usual for its month.</p><div class="split"><span class="swatch member"></span>members +${warmth.member.pct_per_degree.toFixed(1)}% · <span class="swatch casual"></span>casual +${warmth.casual.pct_per_degree.toFixed(1)}%</div></div>
    <div class="sign"><span class="plate">Gust Way</span><b>${fmt.signedPct(wind.all.effect_pct)}</b><p>on a dry day with gusts of 55–70 km/h (${wind.all.periods} days). Wind barely matters.</p>${split(wind)}</div>
    <div class="sign"><span class="plate">Haze Pl</span><b>${fmt.signedPct(air.all.effect_pct)}</b><p>on a "moderate" air-quality day: it does not keep riders home — those are often warm, sunny days.</p>${split(air)}</div>
  </div>
  <div class="panel mt">
    <h3>The city's pulse <small>trips per day, May 2025 – April 2026</small></h3>
    ${resize((width) => pulse(width))}
  </div>
  <p class="footnote">Careful associations, not proof of cause: a rainy hour is also darker and often colder. Trips under a minute or over three hours are left out; members are annual subscribers, casual riders buy single rides or day passes.</p>
</div>
</section>

<section id="rain" class="wrap">
  <h2><span class="bullet blue">R</span>Rain empties the streets — by the hour</h2>
  <p class="sub">For every hour, CityPulse asks: how many trips would this hour have had if it were dry? The answer is the average of dry hours with the same month, the same kind of day and the same hour. Each dot is how far the real count fell from it.</p>
  <div class="panel">
    <h3>Rain <small>trips vs the same hour when dry</small></h3>
    ${resize((width) => effectChart("rain", width))}
  </div>
  <p class="footnote">A drizzle is already enough to lose a quarter of the riders; steady rain halves them. Casual riders react more than members, who still have to get to work. Heavy rain looks milder, but only ${effect(effects, "rain", "heavy rain (≥ 4 mm/h)").periods} hours fell in that band — downpours are short and people are already out.</p>
  <div class="panel mt">
    <h3>The rush hour, washed out <small>average trips per hour, dry vs wet</small></h3>
    ${resize((width) => rush(width))}
  </div>
  <p class="footnote">On workdays the 8 a.m. and 5–6 p.m. peaks are commuters; rain cuts both by roughly half. Plain averages of every wet and dry hour (snow and the blizzard closure left out; wet hours shown where there are at least five), not matched by month like the dots above.</p>
</section>

<section id="weather" class="band">
<div class="wrap">
  <h2><span class="bullet grey">S</span>Snow, wind and air quality</h2>
  <p class="sub">These are judged by the day, against dry days of the same month and kind (snow), or calm days (wind) and good-air days (air quality) — each condition has its own reference band, never including the days being measured.</p>
  <div class="panel"><h3>Snow <small>trips vs dry days of the same month and kind</small></h3>${resize((width) => effectChart("snow", width))}</div>
  <div class="grid2 mt">
    <div class="panel"><h3>Wind <small>dry days, by the day's strongest gust</small></h3>${resize((width) => effectChart("wind", width))}</div>
    <div class="panel"><h3>Air quality <small>dry days, US AQI</small></h3>${resize((width) => effectChart("air quality", width))}</div>
  </div>
  <p class="footnote">Snow is the strongest weather effect of all, though heavy-snow days are few (counts in the tooltips). Wind, surprisingly, barely matters. "Moderate" air is usually ozone on warm, sunny days, so warmth is mixed into that comparison.</p>
</div>
</section>

<section id="warmth" class="wrap">
  <h2><span class="bullet orange">W</span>Warmer days, more riders</h2>
  <p class="sub">On dry, non-holiday days, each day is compared with its own month: how much warmer did it feel than usual, and how many more trips than usual did it have? The slope is the answer, per degree.</p>
  <div class="tiles">
    <div class="tile"><b>+${warmth.all.pct_per_degree.toFixed(1)}%</b><span>trips per °C, all riders (${warmth.all.days} days)</span></div>
    <div class="tile member"><b>+${warmth.member.pct_per_degree.toFixed(1)}%</b><span>members</span></div>
    <div class="tile casual"><b>+${warmth.casual.pct_per_degree.toFixed(1)}%</b><span>casual riders: the most sensitive</span></div>
  </div>
  <div class="panel">
    <h3>The whole season at once <small>trips per dry day, by felt temperature</small></h3>
    ${resize((width) => warmCurve(width))}
  </div>
  <p class="footnote">The curve mixes everything warm months bring — longer days, holidays, tourists. The tiles above hold the season still, which is why they are the answer and the curve is only the picture.</p>
</section>

<section id="rhythm" class="band">
<div class="wrap">
  <h2><span class="bullet green">4</span>A year, day by day</h2>
  <p class="sub">Every square is one New York day, brighter when more people rode. Summer weekends glow, winter fades, and one square in February is outlined: the day the city shut the bikes down.</p>
  <div class="panel">${resize((width) => calendar(width))}</div>
  <div class="grid2 mt">
    <div class="panel"><h3>Trips per day <small>by month</small></h3>${resize((width) => monthBars(width, "trips_per_day", "var(--series-1)", null))}</div>
    <div class="panel"><h3>Mean temperature <small>°C, by month</small></h3>${resize((width) => monthBars(width, "temperature_mean_c", "var(--taxi)", null))}</div>
  </div>
</div>
</section>

<section id="blizzard" class="wrap">
  <h2><span class="bullet red">B</span>Case file: the day with zero trips</h2>
  <div class="case">
    <div class="panel snowfall">${particles(40, "flakes", 5, [4, 9])}<h3>Around the storm <small>trips per day</small></h3>${resize((width) => stormChart(width))}</div>
    <div>
      <span class="big">0 trips</span>
      <p class="muted">Monday 23 February 2026, in a city that averages over 120,000 a day.</p>
      <ol>
        <li>A dbt test flagged it: a whole day with no trips at all. Bug or reality?</li>
        <li>Not a lost file — February's archive reconciled to the row, from the raw CSV to BigQuery. The zero was real.</li>
        <li>The source: a blizzard. Citi Bike shut the whole system from <b>22 Feb 20:00 to 24 Feb 00:00</b> (<a href="https://nyc.streetsblog.org/2026/02/23/mondays-headlines-whiteout-conditions-edition">Streetsblog</a>).</li>
        <li>The window now lives in a sourced table, <code>known_service_closures</code>, and every effect and baseline leaves those hours out — a closed system must not pass for "snow keeps riders home".</li>
      </ol>
      <p class="verdict">A test that fails on real data is still doing its job. The fix was knowledge, not code: one sourced row in a table.</p>
    </div>
  </div>
</section>

<section id="pipeline" class="band">
<div class="wrap">
  <h2><span class="bullet purple">7</span>The pipeline, as a subway map</h2>
  <p class="sub">Two lines run into the lake, change at the manifest and ride one trunk line to these charts. Every stop checks the one before it: rows are counted on the raw bytes and the count must survive every transfer.</p>
  <div class="panel" style="padding:1rem">
    <svg class="metro" viewBox="0 0 1100 330" role="img" aria-label="Pipeline: Open-Meteo and Citi Bike into Bronze, Silver, a manifest, BigQuery raw, dbt and this site">
      <path class="line" d="M60 70H505L600 165" stroke="#ff6319"/>
      <path class="line" d="M60 260H505L600 165" stroke="#00933c"/>
      <path class="line" d="M600 165H1030" stroke="#ee352e"/>
      <g><circle class="stop" cx="60" cy="70" r="8"/><circle class="stop" cx="250" cy="70" r="8"/><circle class="stop" cx="440" cy="70" r="8"/>
        <circle class="stop" cx="60" cy="260" r="8"/><circle class="stop" cx="250" cy="260" r="8"/><circle class="stop" cx="440" cy="260" r="8"/>
        <circle class="hub" cx="600" cy="165" r="13"/><circle class="stop" cx="740" cy="165" r="8"/><circle class="stop" cx="890" cy="165" r="8"/><circle class="hub" cx="1030" cy="165" r="13"/></g>
      <g text-anchor="middle">
        <text x="60" y="44">Open-Meteo</text><text class="small" x="60" y="102">weather · air, hourly</text>
        <text x="250" y="44">Bronze</text><text class="small" x="250" y="102">JSON as received</text>
        <text x="440" y="44">Silver</text><text class="small" x="440" y="102">Parquet, true UTC</text>
        <text x="60" y="296">Citi Bike</text><text class="small" x="60" y="236">monthly ZIP archives</text>
        <text x="250" y="296">Bronze</text><text class="small" x="250" y="236">source record: ETag, CRC-32</text>
        <text x="440" y="296">Silver</text><text class="small" x="440" y="236">every CSV, rows counted</text>
        <text x="600" y="134">Manifest</text><text class="small" x="600" y="200">written last</text>
        <text x="740" y="142">BigQuery raw</text><text class="small" x="740" y="196">a partition per period</text>
        <text x="890" y="142">dbt</text><text class="small" x="890" y="196">staging → marts, tests</text>
        <text x="1030" y="134">This site</text><text class="small" x="1030" y="200">committed exports</text>
      </g>
    </svg>
  </div>
  <div class="grid3 mt">
    <div class="box"><h3><span class="bullet orange" style="width:1.5rem;height:1.5rem;font-size:.8rem;margin-right:.4rem">D</span>Daily line</h3><p>Airflow asks Open-Meteo for each finished New York day — in GMT, two UTC days at a time — and cuts the local day itself, so the days the clocks change have 23 and 25 hours.</p></div>
    <div class="box"><h3><span class="bullet green" style="width:1.5rem;height:1.5rem;font-size:.8rem;margin-right:.4rem">M</span>Monthly line</h3><p>Each month's Citi Bike archive holds several CSV files. Every one is streamed into Parquet; parsed rows must equal the lines counted on the raw bytes before anything is published.</p></div>
    <div class="box"><h3><span class="bullet red" style="width:1.5rem;height:1.5rem;font-size:.8rem;margin-right:.4rem">T</span>Trunk line</h3><p>A load replaces exactly one BigQuery partition and records its count; when new data lands, Airflow's assets trigger dbt, which rebuilds the marts and runs every test.</p></div>
  </div>
  <p class="footnote">Orchestrated by Apache Airflow 3.3 from a versioned image; infrastructure by Terraform in two Google Cloud projects (dev and prod). Python 3.13 · pyarrow · httpx · BigQuery · dbt 1.12 · Observable Framework.</p>
</div>
</section>

<section id="decisions" class="wrap">
  <h2><span class="bullet lime">D</span>Decisions worth explaining</h2>
  <p class="sub">Seventeen decision records explain every choice; these six carry the most weight.</p>
  <div class="grid3">
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0009-control-totals-and-success-manifests.md">ADR 0009</a><h3>Prepare, then publish</h3><p>Each period is built and checked locally before anything is overwritten; the manifest, written last, is the success marker. A failed re-run leaves the last good data alone.</p></div>
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0010-true-utc-instants-and-new-york-days.md">ADR 0010</a><h3>True UTC, New York days</h3><p>Instants are stored in UTC, days are New York days. An API's "local day" turned out to be one fixed offset — wrong twice a year — so the cut is ours.</p></div>
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0015-expected-vs-actual-effects.md">ADR 0015</a><h3>Expected vs actual</h3><p>An effect is actual trips against what like-for-like good weather predicts. Ratios of monthly averages exploded near 0 °C; this does not.</p></div>
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0013-atomic-partition-loads-with-audit.md">ADR 0013</a><h3>One partition, one load</h3><p>Each period replaces exactly its own BigQuery partition, after its file counts are checked, and leaves an audit row. Loading twice gives the same table.</p></div>
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0016-trip-archives-stay-at-the-source.md">ADR 0016</a><h3>Archives stay at the source</h3><p>Bronze keeps a record of each Citi Bike archive — URL, size, ETag, CRC-32 of each file — not a copy: the source is permanent and the record proves what was read.</p></div>
    <div class="box"><a class="adr" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/decisions/0012-two-gcp-projects-built-from-code.md">ADR 0012</a><h3>Built from code, least privilege</h3><p>Two projects by Terraform, one service account with no IAM rights, keyless CI through Workload Identity Federation, budgets and daily query quotas.</p></div>
  </div>
</section>

<section id="quality" class="band">
<div class="wrap">
  <h2><span class="bullet green">Q</span>Quality</h2>
  <p class="sub">Version 1 (March 2026) passed all its tests while 60% of the trips were missing: every row that arrived was consistent. Version 2 counts at the source, so it can see the rows that never arrived.</p>
  <div class="tiles">
    <div class="tile"><b>90</b><span>Python tests, offline</span></div>
    <div class="tile"><b>57</b><span>dbt data tests</span></div>
    <div class="tile"><b>6</b><span>dbt unit tests</span></div>
    <div class="tile"><b>0</b><span>count mismatches, source to warehouse</span></div>
    <div class="tile"><b>17</b><span>decision records</span></div>
  </div>
  <div class="grid2">
    <div class="box"><h3>What is checked</h3><ul class="check yes">
      <li><b>Nothing lost:</b> rows counted on the raw files, reconciled through Silver, the load and a dbt integrity test per day and month.</li>
      <li><b>Time:</b> tests on the days the clocks change; rain moved to the hour it fell in.</li>
      <li><b>The maths:</b> dbt unit tests pin the baselines and the effects on hand-made rows.</li>
      <li><b>Every change:</b> CI runs the Python suite, Terraform validation, dbt against dev (keyless) and the site build.</li>
    </ul></div>
    <div class="box"><h3>What is not</h3><ul class="check no">
      <li><b>No always-on scheduler:</b> Airflow runs on the operator's machine when needed — a cost choice, not an oversight.</li>
      <li><b>No alerting:</b> a failed run shows in Airflow, nobody is paged.</li>
      <li><b>Frozen data:</b> the year is fixed; the pipeline can extend it, the site does not refresh itself.</li>
    </ul></div>
  </div>
</div>
</section>

<section id="limits" class="wrap">
  <h2><span class="bullet grey">L</span>Limits, stated plainly</h2>
  <ul class="limits">
    <li><b>Associations, not causes.</b> A rainy hour is also darker and often colder; the comparison holds the hour, the day and the month still, not everything.</li>
    <li><b>Some bands are thin.</b> Heavy rain: ${effect(effects, "rain", "heavy rain (≥ 4 mm/h)").periods} hours. Heavy snow: ${snow.all.periods} days. Gales: one day. The tooltips give every count.</li>
    <li><b>One point for the whole city.</b> Weather and air quality come from one coordinate (City Hall, Manhattan); a shower over Queens is not a shower over the Bronx.</li>
    <li><b>One year.</b> May 2025 to April 2026 — every season once. Another year could move the numbers.</li>
    <li><b>Air quality is tangled with warmth.</b> "Moderate" days are mostly ozone on sunny days; the +${air.all.effect_pct.toFixed(0)}% is warmth as much as air.</li>
    <li><b>Some trips are left out.</b> Under a minute (false starts) or over three hours (mostly bikes not docked properly).</li>
  </ul>
</section>

<section id="run" class="band run">
<div class="wrap">
  <h2><span class="bullet yellow">N</span>Run it yourself</h2>
  <p class="sub">The offline part needs only <a href="https://docs.astral.sh/uv/">uv</a> and Python 3.12+; the cloud part, a Google Cloud project, Terraform and Docker. <code>make help</code> lists everything.</p>
  <pre><span class="c"># offline: into ./.lake</span>
make setup && make test
uv run citypulse ingest weather --from 2025-03-09   <span class="c"># 23 hours: the clocks went forward</span>
uv run citypulse ingest trips --from 2025-01        <span class="c"># 2,124,475 trips, about a minute</span>

<span class="c"># your own GCP project</span>
make bootstrap ENV=dev BILLING_ACCOUNT=… ORG_ID=…   <span class="c"># project, billing, €5 budget alert</span>
make apply ENV=dev && make airflow-up ENV=dev
make transform ENV=dev                              <span class="c"># dbt build: models + every test</span>
make destroy ENV=dev                                <span class="c"># tear it all down</span></pre>
  <p>About <b>€0 a month</b>: free tiers, no always-on compute, budget alerts and daily query quotas as a hard stop.</p>
  <a class="btn" href="https://github.com/TomasRipsky/CityPulse_Analytics">The repository</a>
  <a class="btn ghost" href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/guide.md">The guide</a>
  <a class="btn ghost" href="https://github.com/TomasRipsky/CityPulse_Analytics/tree/main/docs/decisions">The decisions</a>
</div>
</section>

<footer class="foot"><div class="wrap">
  <span>CityPulse by Tomas Ripsky · data frozen ${summary.first_day} → ${summary.last_day}</span>
  <span>Weather and air quality by <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0) · trips from <a href="https://citibikenyc.com/system-data">Citi Bike System Data</a>; not affiliated with Citi Bike or Lyft</span>
</div></footer>
