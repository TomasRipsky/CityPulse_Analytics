-- grain: one row per (station_id, month, day_type, rider).
-- Station demand for the BI page's map and ranking, filterable by month, kind of day and rider.
-- Trips that do not start at a New York station (e-bikes left outside a dock, a few demo stations
-- elsewhere) are not here; they are in rpt_day_riders, so totals still add up (tested).
with trips as (
    select * from {{ ref('stg_trips') }} where is_plausible and {{ starts_at_nyc_station() }}
),
days as (select local_date, month, day_type from {{ ref('fct_city_day') }})

select
    t.start_station_id as station_id,
    d.month,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    t.member_casual as rider,
    count(*) as trips,
    countif(t.rideable_type = 'electric_bike') as electric_trips,
    round(sum(t.duration_min), 1) as minutes_total
from trips t
join days d on d.local_date = t.start_date_local
group by 1, 2, 3, 4
