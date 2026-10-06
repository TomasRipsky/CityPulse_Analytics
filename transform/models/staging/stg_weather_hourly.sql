-- grain: one row per hourly reading (observed_at), New York.
-- Renames Open-Meteo's variables to say their unit. precipitation_mm, rain_mm, snowfall_cm and
-- wind_gusts_kmh cover the hour ENDING at observed_at (shifted to the hour they describe in
-- int_weather_hours); the others are readings at observed_at.
with source as (
    select * from {{ source('raw', 'weather_hourly') }}
)

select
    observed_at,
    local_date,
    temperature_2m as temperature_c,
    apparent_temperature as apparent_temperature_c,
    precipitation as precipitation_mm,
    rain as rain_mm,
    snowfall as snowfall_cm,
    wind_speed_10m as wind_speed_kmh,
    wind_gusts_10m as wind_gusts_kmh,
    relative_humidity_2m as humidity_pct,
    cloud_cover as cloud_cover_pct,
    weather_code
from source
