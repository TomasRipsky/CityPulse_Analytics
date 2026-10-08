---
title: BI — Citi Bike demand and weather in New York
toc: false
sql:
  day_riders: ./data/bi/rpt_day_riders.parquet
  week_hours: ./data/bi/rpt_week_hours.parquet
  stations: ./data/bi/rpt_stations.parquet
  station_months: ./data/bi/rpt_station_months.parquet
  station_hours: ./data/bi/rpt_station_hours.parquet
  losses: ./data/bi/rpt_weather_losses.parquet
  load_audit: ./data/bi/rpt_load_audit.parquet
  days: ./data/daily.csv
---

```js
import {fmt} from "./components/city.js";
import {downloadButton, monthLabel, shiftMonth} from "./components/bi.js";
const effects = FileAttachment("data/effects.csv").csv({typed: true});
```

```sql id=monthRows
select distinct strftime(month, '%Y-%m') as m from day_riders order by 1
```

```js
// The filter bar: every chart below reads these values.
const months = Array.from(monthRows, (d) => d.m);
const fromInput = Inputs.select(months, {label: "From", value: months[0], format: (m) => monthLabel(m)});
const toInput = Inputs.select(months, {label: "to", value: months.at(-1), format: (m) => monthLabel(m)});
const dayInput = Inputs.radio(["all", "workday", "weekend"], {label: "Days", value: "all"});
const riderInput = Inputs.radio(["all", "member", "casual"], {label: "Riders", value: "all"});
const bikeInput = Inputs.radio(["all", "classic", "electric"], {label: "Bikes", value: "all"});
const from0 = Generators.input(fromInput);
const to0 = Generators.input(toInput);
const dayType = Generators.input(dayInput);
const rider = Generators.input(riderInput);
const bike = Generators.input(bikeInput);
```

```js
// A reversed range reads as the same range; the previous period is as long and ends the month before.
const [from, to] = from0 <= to0 ? [from0, to0] : [to0, from0];
const span = months.indexOf(to) - months.indexOf(from) + 1;
const prevFrom = shiftMonth(from, -span);
const hasPrev = prevFrom >= months[0];
const [pFrom, pTo] = hasPrev ? [prevFrom, shiftMonth(from, -1)] : ["0000-00", "0000-00"];
const rangeLabel = from === to ? monthLabel(from) : `${monthLabel(from)} – ${monthLabel(to)}`;
```

<header class="top" id="top">
  <a class="brand" href="./" aria-label="CityPulse, the story">
    <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="5.5"/><circle cx="24" cy="21" r="5.5"/><path d="M8 21l5-9h8l3 9M13 12l-1.6-3H9.5M21 12l1-3h2.5M16 21l-3-9"/></g></svg>
    CityPulse <span class="badge">BI</span>
  </a>
  <nav aria-label="Sections">
    <a href="#demand">Demand</a>
    <a href="#weather">Weather</a>
    <a href="#stations">Stations</a>
    <a href="#quality">Data quality</a>
    <a href="./">The story</a>
    <a class="gh" href="https://github.com/TomasRipsky/CityPulse_Analytics">GitHub ↗</a>
  </nav>
</header>

<div class="filters">${fromInput}${toInput}${dayInput}${riderInput}${bikeInput}</div>

<section class="wrap bi-head">
  <p class="eyebrow">Self-service · Citi Bike × weather · New York</p>
  <h1>Demand, weather and stations — <em>${rangeLabel}</em></h1>
  <p class="sub">Filter by months, kind of day, rider and bike: the numbers below follow them, and where one cannot, it says so. Data is frozen at April 2026 and computed from 44.5 million trips; how each figure is built is in <a href="https://github.com/TomasRipsky/CityPulse_Analytics/blob/main/docs/guide.md">the guide</a>.</p>
  ${kpiTiles}
</section>

```sql id=kpiRows
select
  strftime(month, '%Y-%m') between ${from} and ${to} as current,
  sum(trips)::DOUBLE as trips,
  (sum(minutes_total) / sum(trips))::DOUBLE as avg_min,
  (sum(case when rider = 'member' then trips else 0 end) / sum(trips))::DOUBLE as member_share,
  (sum(case when bike_type = 'electric' then trips else 0 end) / sum(trips))::DOUBLE as ebike_share
from day_riders
where (strftime(month, '%Y-%m') between ${from} and ${to} or strftime(month, '%Y-%m') between ${pFrom} and ${pTo})
  and (${dayType} = 'all' or day_type = ${dayType})
  and (${rider} = 'all' or rider = ${rider})
  and (${bike} = 'all' or bike_type = ${bike})
group by 1
```

```sql id=dayCounts
select strftime(date::DATE, '%Y-%m') between ${from} and ${to} as current, count(*)::DOUBLE as days
from days
where (strftime(date::DATE, '%Y-%m') between ${from} and ${to} or strftime(date::DATE, '%Y-%m') between ${pFrom} and ${pTo})
  and (${dayType} = 'all' or (${dayType} = 'workday') = (day_type = 'workday'))
group by 1
```

```sql id=lostRows
select strftime(month, '%Y-%m') between ${from} and ${to} as current,
  sum(trips_lost)::DOUBLE as lost, sum(expected_trips)::DOUBLE as expected
from losses
where condition = 'rain'
  and (strftime(month, '%Y-%m') between ${from} and ${to} or strftime(month, '%Y-%m') between ${pFrom} and ${pTo})
  and (${rider} = 'all' or rider = ${rider})
group by 1
```

```js
const pick = (rows, current) => Array.from(rows).find((d) => d.current === current);
const k = pick(kpiRows, true) ?? {}, kp = pick(kpiRows, false);
const dc = pick(dayCounts, true), dp = pick(dayCounts, false);
const lc = pick(lostRows, true);
const perDay = (r, d) => (r && d ? r.trips / d.days : null);
function delta(now, before, {points = false} = {}) {
  if (now == null || before == null || !hasPrev) return html`<small class="delta">no earlier period in the data</small>`;
  const change = points ? 100 * (now - before) : 100 * (now / before - 1);
  // a change is not good or bad here (winter is not a failure): neutral ink, an arrow for direction
  return html`<small class="delta">${change > 0 ? "▲" : change < 0 ? "▼" : "■"} ${Math.abs(change).toFixed(1)}${points ? " pts" : "%"} vs previous ${span === 1 ? "month" : `${span} months`}</small>`;
}
const pct = (x) => (x == null ? "—" : `${(100 * x).toFixed(1)}%`);
const kpiTiles = html`<div class="kpis">
  <div class="kpi"><span>Trips</span><b>${k.trips ? fmt.count(k.trips) : "—"}</b>${delta(k.trips, kp?.trips)}</div>
  <div class="kpi"><span>Trips per day</span><b>${perDay(k, dc) ? fmt.count(Math.round(perDay(k, dc))) : "—"}</b>${delta(perDay(k, dc), perDay(kp, dp))}</div>
  <div class="kpi"><span>Member share</span>${rider === "all" ? html`<b>${pct(k.member_share)}</b>${delta(k.member_share, kp?.member_share, {points: true})}` : html`<b>—</b><small class="delta">the rider filter is on</small>`}</div>
  <div class="kpi"><span>E-bike share</span>${bike === "all" ? html`<b>${pct(k.ebike_share)}</b>${delta(k.ebike_share, kp?.ebike_share, {points: true})}` : html`<b>—</b><small class="delta">the bike filter is on</small>`}</div>
  <div class="kpi"><span>Average ride</span><b>${k.avg_min ? `${k.avg_min.toFixed(1)} min` : "—"}</b>${delta(k.avg_min, kp?.avg_min)}</div>
  <div class="kpi wet"><span>Trips lost to rain</span><b>${lc ? fmt.count(Math.round(lc.lost)) : "—"}</b><small class="delta">${lc ? `${(100 * lc.lost / lc.expected).toFixed(0)}% of the trips rain hours would have had · all days and bikes` : ""}</small></div>
</div>`;
```

<section id="demand" class="band">
<div class="wrap">
  <h2><span class="bullet blue">D</span>Demand</h2>
  <div class="panel">
    <h3>Trips per day <small>stacked by rider · line: mean of the selected days in the last 7</small></h3>
    ${resize((width) => dailyChart(width))}
  </div>
  <div class="grid2 mt">
    <div class="panel"><h3>When the city rides <small>average trips per hour · all bikes</small></h3>${resize((width) => heatChart(width))}</div>
    <div class="panel"><h3>Trips per month <small>stacked by rider</small></h3>${resize((width) => monthChart(width))}</div>
  </div>
  <p class="footnote">The heatmap averages each weekday and hour over the selected months (holidays count as weekends); it has no bike-type split. Trips last 1 minute to 3 hours; hours are New York time.</p>
</div>
</section>

```sql id=dailyRows
-- every selected day of the calendar, with 0 where nobody rode (the blizzard closure)
with cal as (
  select date::DATE as local_date from days
  where strftime(date::DATE, '%Y-%m') between ${from} and ${to}
    and (${dayType} = 'all' or (${dayType} = 'workday') = (day_type = 'workday'))
),
riders as (select unnest(['member', 'casual']) as rider),
t as (
  select local_date, rider, sum(trips) as trips from day_riders
  where strftime(month, '%Y-%m') between ${from} and ${to}
    and (${bike} = 'all' or bike_type = ${bike})
  group by 1, 2
)
select c.local_date, r.rider, coalesce(t.trips, 0)::DOUBLE as trips
from cal c cross join riders r
left join t on t.local_date = c.local_date and t.rider = r.rider
where ${rider} = 'all' or r.rider = ${rider}
order by 1
```

```sql id=dailyTotals
-- the line: mean of the selected days within the last 7 calendar days
with cal as (
  select date::DATE as local_date from days
  where strftime(date::DATE, '%Y-%m') between ${from} and ${to}
    and (${dayType} = 'all' or (${dayType} = 'workday') = (day_type = 'workday'))
),
t as (
  select local_date, sum(trips) as trips from day_riders
  where strftime(month, '%Y-%m') between ${from} and ${to}
    and (${rider} = 'all' or rider = ${rider})
    and (${bike} = 'all' or bike_type = ${bike})
  group by 1
),
tot as (select c.local_date, coalesce(t.trips, 0) as trips from cal c left join t using (local_date))
select local_date, trips::DOUBLE as trips,
  avg(trips) over (order by local_date range between interval 6 days preceding and current row)::DOUBLE as mean7
from tot order by 1
```

```sql id=monthRowsFiltered
select strftime(month, '%Y-%m') as m, rider, sum(trips)::DOUBLE as trips
from day_riders
where strftime(month, '%Y-%m') between ${from} and ${to}
  and (${dayType} = 'all' or day_type = ${dayType})
  and (${rider} = 'all' or rider = ${rider})
  and (${bike} = 'all' or bike_type = ${bike})
group by 1, 2 order by 1
```

```sql id=heatRows
with t as (
  select month, weekday_number, day_type, local_hour, sum(trips) as trips, max(days) as days
  from week_hours
  where strftime(month, '%Y-%m') between ${from} and ${to}
    and (${dayType} = 'all' or day_type = ${dayType})
    and (${rider} = 'all' or rider = ${rider})
  group by 1, 2, 3, 4
)
select weekday_number::INTEGER as weekday_number, local_hour::INTEGER as local_hour,
  (sum(trips) / sum(days))::DOUBLE as avg_trips
from t group by 1, 2
```

```js
const riderColor = {domain: ["member", "casual"], range: ["var(--series-1)", "var(--series-2)"], legend: true};
const daily = Array.from(dailyRows, (d) => ({...d, local_date: new Date(d.local_date)}));
const dayTotals = Array.from(dailyTotals, (d) => ({...d, local_date: new Date(d.local_date)}));
function dailyChart(width) {
  return Plot.plot({
    width, height: 260, marginLeft: 48,
    x: {label: null},
    y: {label: "trips per day", grid: true, tickFormat: "s"},
    color: riderColor,
    marks: [
      Plot.rectY(daily, {x: "local_date", interval: "day", y: "trips", fill: "rider", order: ["member", "casual"]}),
      Plot.lineY(dayTotals, {x: "local_date", y: "mean7", stroke: "var(--ink)", strokeWidth: 1.5, curve: "monotone-x"}),
      Plot.tip(dayTotals, Plot.pointerX({x: "local_date", y: "trips", title: (d) => `${fmt.date(d.local_date)}\n${d.trips === 0 ? "0 trips" : `${fmt.count(d.trips)} trips`}\n7-day mean ${fmt.count(Math.round(d.mean7))}`}))
    ]
  });
}
const weekdays = [2, 3, 4, 5, 6, 7, 1]; // BigQuery's dayofweek: 1 = Sunday
function heatChart(width) {
  return Plot.plot({
    width, height: 240, marginLeft: 40, padding: 0.06,
    x: {label: "hour", ticks: [0, 6, 12, 18, 23]},
    y: {label: null, domain: weekdays, tickFormat: (d) => ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d - 1]},
    color: {type: "linear", range: ["#162238", "#8cc0ff"], label: "avg trips per hour", legend: true, tickFormat: "s"},
    marks: [
      Plot.cell(Array.from(heatRows), {x: "local_hour", y: "weekday_number", fill: "avg_trips", inset: 0.5, rx: 2, tip: true,
        title: (d) => `${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.weekday_number - 1]} ${d.local_hour}:00\n${fmt.count(Math.round(d.avg_trips))} trips on average`})
    ]
  });
}
function monthChart(width) {
  return Plot.plot({
    width, height: 240, marginLeft: 44,
    x: {label: null, type: "band", tickFormat: (m) => monthLabel(m, width < 480)},
    y: {label: null, grid: true, tickFormat: "s"},
    color: riderColor,
    marks: [
      Plot.barY(Array.from(monthRowsFiltered), {x: "m", y: "trips", fill: "rider", order: ["member", "casual"], insetLeft: 3, insetRight: 3, tip: true}),
      Plot.ruleY([0], {stroke: "var(--mist)"})
    ]
  });
}
```

<section id="weather" class="wrap">
  <h2><span class="bullet red">W</span>Weather</h2>
  <div class="grid2">
    <div class="panel"><h3>Trips lost to rain <small>expected − actual, by month and rain band</small></h3>${resize((width) => lossChart(width))}</div>
    <div class="panel"><h3>Snow days <small>in the selected months</small></h3>${snowTable}</div>
  </div>
  <div class="panel mt"><h3>Effects by condition <small>the whole year · trips vs good conditions</small></h3>${effectsTable}</div>
  <p class="footnote">"Lost" compares each rainy hour with the same hour, kind of day and month when it was dry (the method on <a href="./#rain">the story page</a>); it follows the month and rider filters, all days and bikes. Snow is measured per day and overlaps with rain, so the two are never added up. Effects are year-level measurements: they do not follow the filters.</p>
</section>

```sql id=lossRows
select strftime(month, '%Y-%m') as m, band, band_order::INTEGER as band_order, sum(trips_lost)::DOUBLE as lost
from losses
where condition = 'rain' and strftime(month, '%Y-%m') between ${from} and ${to}
  and (${rider} = 'all' or rider = ${rider})
group by 1, 2, 3 order by 1, 3
```

```sql id=snowRows
select date, snowfall_cm::DOUBLE as snowfall_cm, trips::DOUBLE as trips, temperature_mean_c::DOUBLE as temperature_mean_c
from days
where snowfall_cm > 0 and strftime(date::DATE, '%Y-%m') between ${from} and ${to}
order by date
```

```js
const bands = ["drizzle (< 1 mm/h)", "rain (1–4 mm/h)", "heavy rain (≥ 4 mm/h)"];
function lossChart(width) {
  return Plot.plot({
    width, height: 260, marginLeft: 48,
    x: {label: null, type: "band", tickFormat: (m) => monthLabel(m, width < 480)},
    y: {label: "trips lost", grid: true, tickFormat: "s"},
    color: {domain: bands, range: ["#86b6ef", "#3987e5", "#1c5cab"], legend: true},
    marks: [
      Plot.barY(Array.from(lossRows), {x: "m", y: "lost", fill: "band", order: bands, insetLeft: 3, insetRight: 3, tip: true,
        title: (d) => `${monthLabel(d.m)} · ${d.band}\n${fmt.count(Math.round(d.lost))} trips lost`}),
      Plot.ruleY([0], {stroke: "var(--mist)"})
    ]
  });
}
const snow = Array.from(snowRows);
const snowTable = snow.length
  ? Inputs.table(snow, {
      columns: ["date", "snowfall_cm", "trips", "temperature_mean_c"],
      header: {date: "Day", snowfall_cm: "Snow (cm)", trips: "Trips (everyone)", temperature_mean_c: "Mean °C"},
      format: {date: (d) => fmt.date(new Date(d)), trips: (d) => (d === 0 ? "0 — system closed" : fmt.count(d))},
      rows: 8, select: false
    })
  : html`<p class="muted">No snow in the selected months.</p>`;
const effectRows = d3.groups(effects.filter((d) => !d.is_reference), (d) => `${d.condition}|${d.band}`).map(([, v]) => ({
  condition: v[0].condition, band: v[0].band,
  all: v.find((d) => d.rider === "all")?.effect_pct,
  member: v.find((d) => d.rider === "member")?.effect_pct,
  casual: v.find((d) => d.rider === "casual")?.effect_pct,
  periods: v.find((d) => d.rider === "all")?.periods
}));
const signed = (d) => (d == null ? "—" : fmt.signedPct(d));
const effectsTable = Inputs.table(effectRows, {
  header: {condition: "Condition", band: "Band", all: "All riders", member: "Members", casual: "Casual", periods: "Periods"},
  format: {all: signed, member: signed, casual: signed},
  rows: 14, select: false
});
```

<section id="stations" class="band">
<div class="wrap">
  <h2><span class="bullet green">S</span>Stations</h2>
  <div class="map-head">${metricInput}</div>
  <div class="grid2">
    <div class="panel">${resize((width) => stationMap(width))}</div>
    <div class="panel station-panel">${stationPanel}</div>
  </div>
  <div class="panel mt">
    <div class="table-head"><h3>All stations <small>pick a row to open it above · click a column to sort</small></h3>${downloadButton(stationList, `citypulse-stations-${from}-${to}-${dayType}-${rider}-${bike}.csv`)}</div>
    ${stationTable}
  </div>
  <p class="footnote">Trips and shares follow every filter; a share that a filter fixes (members when one rider type is picked, e-bikes when one bike type is) shows "—". The rain effect is a year-level, all-rider measurement and does not follow the filters. Trips that do not start at a New York station (about 22,000 e-bikes left outside a dock) count in the totals above but not here. A station's rain effect compares its rain hours with its own dry hours (same month, kind of day and hour) over its active months, and is shown only where at least 1,000 trips were expected in the rain; the ± is the counting noise alone.</p>
</div>
</section>

```js
const metricInput = Inputs.radio(["trips", "member share", "e-bike share", "rain effect"], {label: "Colour by", value: "trips"});
const metric = Generators.input(metricInput);
```

```sql id=stationRows
with m as (
  select station_id,
    sum(case ${bike} when 'electric' then electric_trips when 'classic' then trips - electric_trips else trips end) as trips,
    sum(case when rider = 'member' then case ${bike} when 'electric' then electric_trips when 'classic' then trips - electric_trips else trips end else 0 end) as member_trips,
    sum(electric_trips) as electric_trips, sum(trips) as all_bike_trips
  from station_months
  where strftime(month, '%Y-%m') between ${from} and ${to}
    and (${dayType} = 'all' or day_type = ${dayType})
    and (${rider} = 'all' or rider = ${rider})
  group by 1
)
select s.station_id, s.station_name, s.lat::DOUBLE as lat, s.lng::DOUBLE as lng,
  m.trips::DOUBLE as trips,
  (m.member_trips / nullif(m.trips, 0))::DOUBLE as member_share,
  (m.electric_trips / nullif(m.all_bike_trips, 0))::DOUBLE as ebike_share,
  s.active_months::INTEGER as active_months,
  s.rain_effect_pct::DOUBLE as rain_effect_pct,
  s.rain_trips::DOUBLE as rain_trips, s.rain_expected_trips::DOUBLE as rain_expected_trips
from stations s join m using (station_id)
where m.trips > 0
order by m.trips desc
```

```js
const stationList = Array.from(stationRows, (d, i) => ({rank: i + 1, ...d}));
const rainNoise = (d) => (d.rain_effect_pct == null ? null : (196 * Math.sqrt(d.rain_trips)) / d.rain_expected_trips);
const stationTable = Inputs.table(stationList, {
  columns: ["rank", "station_name", "trips", "member_share", "ebike_share", "rain_effect_pct"],
  header: {rank: "#", station_name: "Station", trips: "Trips", member_share: "Members", ebike_share: "E-bikes", rain_effect_pct: "Rain effect (year, all riders)"},
  format: {trips: fmt.count, member_share: (d) => (rider === "all" ? pct(d) : "—"), ebike_share: (d) => (bike === "all" ? pct(d) : "—"), rain_effect_pct: (d) => (d == null ? "too little rain data" : fmt.signedPct(d))},
  width: {rank: 40, station_name: 280},
  multiple: false, required: false, rows: 12
});
// the picked station survives a filter change (the table is rebuilt, its selection is not)
stationTable.addEventListener("input", () => stationTable.value && setPicked(stationTable.value.station_id));
```

```js
const pickedId = Mutable(null);
const setPicked = (id) => (pickedId.value = id);
```

```js
const station = stationList.find((d) => d.station_id === pickedId) ?? stationList[0];
// a share fixed by a filter (all members, all e-bikes) would paint one colour: fall back to trips
const metricShown = (metric === "member share" && rider !== "all") || (metric === "e-bike share" && bike !== "all") ? "trips" : metric;
const metricSpec = {
  "trips": {value: "trips", color: {type: "sqrt", range: ["#3d6bb3", "#cde2fb"], label: "trips", legend: true, tickFormat: "s"}},
  "member share": {value: (d) => 100 * d.member_share, color: {type: "linear", range: ["#3d6bb3", "#cde2fb"], label: "member share (%)", legend: true}},
  "e-bike share": {value: (d) => 100 * d.ebike_share, color: {type: "linear", range: ["#3d6bb3", "#cde2fb"], label: "e-bike share (%)", legend: true}},
  "rain effect": {value: "rain_effect_pct", color: {type: "diverging", pivot: 0, range: ["#e66767", "#8a8f99", "#3987e5"], label: "rain effect, year, all riders (%)", legend: true}}
}[metricShown];
function stationMap(width) {
  if (!station) return html`<p class="muted">No station has trips in these filters.</p>`;
  const shown = metricShown === "rain effect" ? stationList.filter((d) => d.rain_effect_pct != null) : stationList;
  return Plot.plot({
    width, height: Math.min(560, width * 1.15),
    projection: {type: "mercator", domain: {type: "MultiPoint", coordinates: stationList.map((d) => [d.lng, d.lat])}, inset: 8},
    color: metricSpec.color,
    r: {type: "sqrt", range: [1.2, 7]},
    marks: [
      Plot.dot(shown, {x: "lng", y: "lat", r: "trips", fill: metricSpec.value, fillOpacity: 0.85, tip: true,
        title: (d) => `${d.station_name}\n${fmt.count(d.trips)} trips · members ${pct(d.member_share)} · e-bikes ${pct(d.ebike_share)}${d.rain_effect_pct == null ? "" : `\nrain effect ${fmt.signedPct(d.rain_effect_pct)}`}`}),
      Plot.dot([station], {x: "lng", y: "lat", r: 9, stroke: "var(--taxi)", strokeWidth: 2.5})
    ]
  });
}
```

```sql id=stationMonthRows
select strftime(month, '%Y-%m') as m, rider, sum(trips)::DOUBLE as trips
from station_months
where station_id = ${station?.station_id ?? ""}
  and (${dayType} = 'all' or day_type = ${dayType})
group by 1, 2 order by 1
```

```sql id=stationHourRows
-- an average day of each kind: the year has about 250 workdays and 115 weekend days and holidays
with d as (
  select case when day_type = 'workday' then 'workday' else 'weekend' end as day_type, count(*) as n
  from days group by 1
)
select h.day_type, h.local_hour::INTEGER as local_hour, (sum(h.trips) / any_value(d.n))::DOUBLE as trips
from station_hours h join d using (day_type)
where h.station_id = ${station?.station_id ?? ""}
group by 1, 2 order by 2
```

```js
const noise = station ? rainNoise(station) : null;
const stationPanel = !station ? html`<p class="muted">No station has trips in these filters.</p>` : html`
  <p class="eyebrow">Station · ${station.active_months} active months</p>
  <h3 class="station-name">${station.station_name}</h3>
  <div class="tiles mini">
    <div class="tile"><b>${fmt.count(station.trips)}</b><span>trips in the filters</span></div>
    <div class="tile member"><b>${rider === "all" ? pct(station.member_share) : "—"}</b><span>members</span></div>
    <div class="tile"><b>${station.rain_effect_pct == null ? "—" : `${fmt.signedPct(station.rain_effect_pct)}`}</b><span>${station.rain_effect_pct == null ? "too little rain data" : `in the rain · year, all riders · ±${Math.max(1, Math.round(noise))} pts`}</span></div>
  </div>
  <p class="mini-title">Trips per month · by rider, every month, your kind-of-day filter</p>
  ${resize((width) => Plot.plot({
    width, height: 170, marginLeft: 40,
    x: {label: null, type: "band", tickFormat: (m) => monthLabel(m, true)},
    y: {label: null, grid: true, tickFormat: "s"},
    color: riderColor,
    marks: [Plot.barY(Array.from(stationMonthRows), {x: "m", y: "trips", fill: "rider", order: ["member", "casual"], insetLeft: 2, insetRight: 2, tip: true}), Plot.ruleY([0], {stroke: "var(--mist)"})]
  }))}
  <p class="mini-title">Its average day · trips per hour, over the year</p>
  ${resize((width) => Plot.plot({
    width, height: 170, marginLeft: 40,
    x: {label: null, ticks: [0, 6, 12, 18, 23]},
    y: {label: null, grid: true, tickFormat: "s"},
    color: {domain: ["workday", "weekend"], range: ["var(--ink)", "var(--taxi)"], legend: true},
    marks: [Plot.lineY(Array.from(stationHourRows), {x: "local_hour", y: "trips", stroke: "day_type", strokeWidth: 2, curve: "monotone-x", tip: true})]
  }))}`;
```

<section id="quality" class="wrap">
  <h2><span class="bullet grey">Q</span>Data quality</h2>
  <p class="sub">Every period loaded into the warehouse is counted at the source first; the load must match it. ${auditSummary}</p>
  ${auditTiles}
  <div class="panel">${auditTable}</div>
  <p class="footnote">Rows are as the sources publish them: hourly readings for weather and air quality, one row per trip for Citi Bike (before the 1 min – 3 h filter). Last load: ${lastLoad}. Data frozen May 2025 – April 2026.</p>
</section>

```sql id=auditRows
select source, strftime(month, '%Y-%m') as m, periods::INTEGER as periods, source_rows::DOUBLE as source_rows,
  loaded_rows::DOUBLE as loaded_rows, mismatched_periods::INTEGER as mismatched, last_loaded_at
from load_audit order by source, month
```

```js
const audit = Array.from(auditRows);
const sourceName = {citibike: "Citi Bike trips", weather: "Weather (hourly)", air_quality: "Air quality (hourly)"};
const bySource = d3.rollups(audit, (v) => ({periods: d3.sum(v, (d) => d.periods), rows: d3.sum(v, (d) => d.loaded_rows), mismatched: d3.sum(v, (d) => d.mismatched)}), (d) => d.source);
const mismatched = d3.sum(audit, (d) => d.mismatched);
const auditSummary = mismatched === 0 ? html`<b>All ${fmt.count(d3.sum(audit, (d) => d.periods))} periods match.</b>` : html`<b>${mismatched} periods do not match.</b>`;
const auditTiles = html`<div class="tiles">${bySource.map(([source, s]) => html`<div class="tile"><b>${fmt.count(s.rows)}</b><span>${sourceName[source] ?? source} · ${s.periods} periods · ${s.mismatched === 0 ? "✓ all match" : `${s.mismatched} mismatched`}</span></div>`)}</div>`;
const lastLoaded = d3.max(audit, (d) => d.last_loaded_at);
const lastLoad = lastLoaded ? d3.utcFormat("%-d %B %Y, %H:%M UTC")(new Date(lastLoaded)) : "—";
const auditTable = Inputs.table(audit, {
  columns: ["source", "m", "periods", "source_rows", "loaded_rows", "mismatched"],
  header: {source: "Source", m: "Month", periods: "Periods", source_rows: "Rows at the source", loaded_rows: "Rows loaded", mismatched: "Mismatched"},
  format: {source: (d) => sourceName[d] ?? d, m: (d) => monthLabel(d), source_rows: fmt.count, loaded_rows: fmt.count},
  rows: 12, select: false
});
```

<footer class="foot"><div class="wrap">
  <span>CityPulse BI · data frozen 2025-05-01 → 2026-04-30 · <a href="./">the story</a></span>
  <span>Weather and air quality by <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0) · trips from <a href="https://citibikenyc.com/system-data">Citi Bike System Data</a>; not affiliated with Citi Bike or Lyft</span>
</div></footer>
