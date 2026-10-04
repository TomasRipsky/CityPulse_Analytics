-- grain: one row per New York day (local_date) with weather.
with hours as (
    select * from {{ ref('int_weather_hours') }}
)

select
    local_date,
    count(*) as hours,
    countif(precipitation_mm is not null) as hours_with_precipitation_known,
    round(avg(temperature_c), 1) as temperature_mean_c,
    min(temperature_c) as temperature_min_c,
    max(temperature_c) as temperature_max_c,
    round(avg(apparent_temperature_c), 1) as apparent_temperature_mean_c,
    round(sum(precipitation_mm), 1) as precipitation_mm,
    round(sum(rain_mm), 1) as rain_mm,
    round(sum(snowfall_cm), 1) as snowfall_cm,
    countif(precipitation_mm >= 0.1) as wet_hours,
    round(avg(wind_speed_kmh), 1) as wind_speed_mean_kmh,
    max(wind_gusts_kmh) as wind_gusts_max_kmh,
    round(avg(humidity_pct)) as humidity_mean_pct,
    round(avg(cloud_cover_pct)) as cloud_cover_mean_pct
from hours
group by local_date
