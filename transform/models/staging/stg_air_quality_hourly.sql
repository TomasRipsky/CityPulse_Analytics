-- grain: one row per hourly reading (observed_at), New York.
with source as (
    select * from {{ source('raw', 'air_quality_hourly') }}
)

select
    observed_at,
    local_date,
    pm2_5 as pm2_5_ugm3,
    pm10 as pm10_ugm3,
    ozone as ozone_ugm3,
    nitrogen_dioxide as no2_ugm3,
    us_aqi
from source
