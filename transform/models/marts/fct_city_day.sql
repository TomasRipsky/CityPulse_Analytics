-- grain: one row per New York day (local_date), from the first to the last day with weather.
-- Trips are 0 on a day with none in a loaded month (e.g. an outage) and null when the day's month
-- was never loaded: "no data" and "nobody rode" stay different.
with calendar as (select * from {{ ref('int_calendar_days') }}),
closures as (select * from {{ ref('known_service_closures') }}),
weather as (select * from {{ ref('int_weather_days') }}),
air as (select * from {{ ref('int_air_days') }}),
trips as (select * from {{ ref('int_trips_days') }})

select
    c.local_date,
    c.weekday,
    c.day_type,
    c.holiday,
    c.month,
    c.season,
    c.trips_loaded,
    -- any part of the day inside a known system closure: left out of every effect and baseline
    exists(
        select 1 from closures x
        where x.closed_from < datetime(date_add(c.local_date, interval 1 day))
          and x.closed_until > datetime(c.local_date)
    ) as service_closed,
    if(c.trips_loaded, coalesce(t.trips, 0), null) as trips,
    if(c.trips_loaded, coalesce(t.member_trips, 0), null) as member_trips,
    if(c.trips_loaded, coalesce(t.casual_trips, 0), null) as casual_trips,
    if(c.trips_loaded, coalesce(t.electric_trips, 0), null) as electric_trips,
    if(c.trips_loaded, coalesce(t.all_trips, 0), null) as all_trips,
    if(c.trips_loaded, t.duration_median_min, null) as duration_median_min,
    if(c.trips_loaded, t.active_stations, null) as active_stations,
    w.temperature_mean_c,
    w.temperature_min_c,
    w.temperature_max_c,
    w.apparent_temperature_mean_c,
    w.precipitation_mm,
    w.rain_mm,
    w.snowfall_cm,
    w.wet_hours,
    w.wind_speed_mean_kmh,
    w.wind_gusts_max_kmh,
    w.humidity_mean_pct,
    w.cloud_cover_mean_pct,
    w.hours_with_precipitation_known,
    a.aqi_mean,
    a.aqi_max,
    a.aqi_category,
    a.pm2_5_mean_ugm3,
    -- dry: less than 1 mm of precipitation and no snow over the day (null when not fully known)
    w.precipitation_mm < 1 and w.snowfall_cm = 0 as is_dry
from calendar c
left join weather w using (local_date)
left join air a using (local_date)
left join trips t using (local_date)
