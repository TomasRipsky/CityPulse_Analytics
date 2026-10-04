{{ config(materialized='table') }}
-- grain: one row per New York day (local_date) on which at least one trip started.
with trips as (
    select * from {{ ref('stg_trips') }}
)

select
    start_date_local as local_date,
    count(*) as all_trips,
    countif(is_plausible) as trips,
    countif(is_plausible and member_casual = 'member') as member_trips,
    countif(is_plausible and member_casual = 'casual') as casual_trips,
    countif(is_plausible and rideable_type = 'electric_bike') as electric_trips,
    countif(is_plausible and rideable_type = 'classic_bike') as classic_trips,
    approx_quantiles(if(is_plausible, duration_min, null), 100)[offset(50)] as duration_median_min,
    count(distinct if(is_plausible, start_station_id, null)) as active_stations
from trips
group by start_date_local
