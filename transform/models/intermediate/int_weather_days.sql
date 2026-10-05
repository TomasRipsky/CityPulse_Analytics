-- grain: one row per New York day (local_date) with weather.
-- Interval totals (precipitation, rain, snow, wet hours, strongest gust) are null unless every
-- hour of the day is known: a day whose last hour is missing must not look complete and dry.
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
    if(countif(precipitation_mm is null) = 0, round(sum(precipitation_mm), 1), null) as precipitation_mm,
    if(countif(rain_mm is null) = 0, round(sum(rain_mm), 1), null) as rain_mm,
    if(countif(snowfall_cm is null) = 0, round(sum(snowfall_cm), 1), null) as snowfall_cm,
    if(countif(precipitation_mm is null) = 0, countif(precipitation_mm >= 0.1), null) as wet_hours,
    round(avg(wind_speed_kmh), 1) as wind_speed_mean_kmh,
    if(countif(wind_gusts_kmh is null) = 0, max(wind_gusts_kmh), null) as wind_gusts_max_kmh,
    round(avg(humidity_pct)) as humidity_mean_pct,
    round(avg(cloud_cover_pct)) as cloud_cover_mean_pct
from hours
group by local_date
