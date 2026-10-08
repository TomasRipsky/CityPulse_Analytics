{{ config(materialized='table') }}
-- grain: one row per (hour_start, station_id, rider, bike_type) with at least one plausible trip;
-- station_id is null for trips that do not start at a New York station.
-- The one scan of stg_trips behind the BI page's report models: they all read this table (about
-- half as many rows, a fraction of the bytes) instead of scanning 44 million trips each.
select
    start_hour as hour_start,
    start_date_local as local_date,
    start_hour_local as local_hour,
    if({{ starts_at_nyc_station() }}, start_station_id, null) as station_id,
    member_casual as rider,
    case rideable_type when 'electric_bike' then 'electric' when 'classic_bike' then 'classic' end as bike_type,
    count(*) as trips,
    sum(duration_min) as minutes_total
from {{ ref('stg_trips') }}
where is_plausible
group by 1, 2, 3, 4, 5, 6
