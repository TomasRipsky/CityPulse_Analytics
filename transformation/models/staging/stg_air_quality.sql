-- stg_air_quality.sql
-- Vista ligera sobre la tabla raw de calidad del aire.

with source as (
    select * from {{ source('citypulse_staging', 'air_quality') }}
),

staged as (
    select
        cast(timestamp as timestamp)        as timestamp,
        cast(date as date)                  as date,
        cast(pm2_5 as float64)              as pm2_5,
        cast(pm10 as float64)               as pm10,
        cast(ozone as float64)              as ozone,
        cast(us_aqi as int64)               as us_aqi,
        cast(aqi_category as string)        as aqi_category,
        cast(location as string)            as location
    from source
    where timestamp is not null
      and date is not null
)

select * from staged