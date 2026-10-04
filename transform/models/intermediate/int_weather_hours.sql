-- grain: one row per hour (hour_start, UTC), New York weather for the hour [hour_start, +1h).
-- Readings (temperature, wind speed, humidity, clouds, weather code) are taken at hour_start.
-- Interval variables arrive stamped at the END of their hour, so the hour starting at h takes them
-- from the row stamped h + 1h; if that row is missing (end of data, a gap), they are null, not 0.
with readings as (
    select * from {{ ref('stg_weather_hourly') }}
),

with_next as (
    select
        *,
        lead(observed_at) over (order by observed_at) as next_observed_at,
        lead(precipitation_mm) over (order by observed_at) as next_precipitation_mm,
        lead(rain_mm) over (order by observed_at) as next_rain_mm,
        lead(snowfall_cm) over (order by observed_at) as next_snowfall_cm,
        lead(wind_gusts_kmh) over (order by observed_at) as next_wind_gusts_kmh
    from readings
)

select
    observed_at as hour_start,
    date(observed_at, '{{ var("timezone") }}') as local_date,
    extract(hour from datetime(observed_at, '{{ var("timezone") }}')) as local_hour,
    temperature_c,
    apparent_temperature_c,
    wind_speed_kmh,
    humidity_pct,
    cloud_cover_pct,
    weather_code,
    if(next_observed_at = timestamp_add(observed_at, interval 1 hour), next_precipitation_mm, null) as precipitation_mm,
    if(next_observed_at = timestamp_add(observed_at, interval 1 hour), next_rain_mm, null) as rain_mm,
    if(next_observed_at = timestamp_add(observed_at, interval 1 hour), next_snowfall_cm, null) as snowfall_cm,
    if(next_observed_at = timestamp_add(observed_at, interval 1 hour), next_wind_gusts_kmh, null) as wind_gusts_kmh
from with_next
