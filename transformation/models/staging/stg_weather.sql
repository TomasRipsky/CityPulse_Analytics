-- stg_weather.sql
-- Vista ligera sobre la tabla raw de clima.

with source as (
    select * from {{ source('citypulse_staging', 'weather') }}
),

staged as (
    select
        --Casteo y renombrado
        cast(timestamp as timestamp)      as timestamp,
        cast(date as date)                as date,
        cast(temperature_c as float64)    as temperature_c,
        cast(precipitation_mm as float64) as precipitation_mm,
        cast(wind_speed_kmh as float64)   as wind_speed_kmh,
        cast(humidity_pct as float64)     as humidity_pct,
        cast(location as string)          as location
    from source
    where timestamp is not null
      and date is not null
)

select * from staged
