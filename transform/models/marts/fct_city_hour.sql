-- grain: one row per hour (hour_start, UTC) with weather; local_date/local_hour in New York.
-- 23 rows on the spring-forward day, 25 on the fall-back day (two local 01:00 hours).
with hours as (select * from {{ ref('int_weather_hours') }}),
calendar as (select * from {{ ref('int_calendar_days') }}),
trips as (select * from {{ ref('int_trips_hours') }}),
air as (select observed_at, us_aqi from {{ ref('stg_air_quality_hourly') }})

select
    h.hour_start,
    h.local_date,
    h.local_hour,
    c.day_type,
    c.month,
    c.trips_loaded,
    if(c.trips_loaded, coalesce(t.trips, 0), null) as trips,
    if(c.trips_loaded, coalesce(t.member_trips, 0), null) as member_trips,
    if(c.trips_loaded, coalesce(t.casual_trips, 0), null) as casual_trips,
    if(c.trips_loaded, coalesce(t.electric_trips, 0), null) as electric_trips,
    h.temperature_c,
    h.apparent_temperature_c,
    h.precipitation_mm,
    h.rain_mm,
    h.snowfall_cm,
    h.wind_speed_kmh,
    h.wind_gusts_kmh,
    h.humidity_pct,
    h.cloud_cover_pct,
    h.weather_code,
    a.us_aqi,
    h.precipitation_mm = 0 and coalesce(h.snowfall_cm, 0) = 0 as is_dry
from hours h
join calendar c using (local_date)
left join trips t using (hour_start)
left join air a on a.observed_at = h.hour_start
