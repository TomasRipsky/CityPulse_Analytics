{{ config(materialized='table') }}
-- grain: one row per hour (start_hour, UTC) in which at least one trip started.
-- Counts use plausible trips only (1 min – 3 h); all_trips keeps the total for reconciliation.
with trips as (
    select * from {{ ref('stg_trips') }}
)

select
    start_hour as hour_start,
    any_value(start_date_local) as local_date,
    count(*) as all_trips,
    countif(is_plausible) as trips,
    countif(is_plausible and member_casual = 'member') as member_trips,
    countif(is_plausible and member_casual = 'casual') as casual_trips,
    countif(is_plausible and rideable_type = 'electric_bike') as electric_trips,
    countif(is_plausible and rideable_type = 'classic_bike') as classic_trips,
    approx_quantiles(if(is_plausible, duration_min, null), 100)[offset(50)] as duration_median_min
from trips
group by start_hour
