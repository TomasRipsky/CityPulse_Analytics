-- stg_citibike.sql
-- Vista ligera sobre la tabla raw de Citibike.

with source as (
    select * from {{ source('citypulse_staging', 'citibike') }}
),

staged as (
    select
        cast(ride_id as string)               as ride_id,
        cast(rideable_type as string)         as rideable_type,
        cast(started_at as timestamp)         as started_at,
        cast(ended_at as timestamp)           as ended_at,
        cast(start_station_name as string)    as start_station_name,
        cast(end_station_name as string)      as end_station_name,
        cast(start_lat as float64)            as start_lat,
        cast(start_lng as float64)            as start_lng,
        cast(end_lat as float64)              as end_lat,
        cast(end_lng as float64)              as end_lng,
        cast(member_casual as string)         as member_casual,
        cast(duration_minutes as float64)     as duration_minutes,
        cast(year as int64)                   as year,
        cast(month as int64)                  as month
    from source
    where started_at is not null
      and duration_minutes > 0
      -- Filtramos viajes cuya fecha de inicio no corresponde al mes del archivo.
      -- Citibike incluye en cada ZIP algunos viajes de los últimos días del mes
      -- anterior, lo que genera duplicados en daily_mobility_summary.
      and extract(year from started_at)  = cast(year as int64)
      and extract(month from started_at) = cast(month as int64)
)

select * from staged
