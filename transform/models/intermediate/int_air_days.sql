-- grain: one row per New York day (local_date) with air quality.
-- Category: US EPA bands applied to the day's mean AQI.
with hours as (
    select * from {{ ref('stg_air_quality_hourly') }}
),

daily as (
    select
        local_date,
        count(*) as hours,
        round(avg(us_aqi)) as aqi_mean,
        max(us_aqi) as aqi_max,
        round(avg(pm2_5_ugm3), 1) as pm2_5_mean_ugm3,
        round(avg(ozone_ugm3), 1) as ozone_mean_ugm3,
        round(avg(no2_ugm3), 1) as no2_mean_ugm3
    from hours
    group by local_date
)

select
    *,
    case
        when aqi_mean <= 50 then 'good'
        when aqi_mean <= 100 then 'moderate'
        when aqi_mean <= 150 then 'unhealthy for sensitive groups'
        when aqi_mean <= 200 then 'unhealthy'
        when aqi_mean <= 300 then 'very unhealthy'
        else 'hazardous'
    end as aqi_category
from daily
