-- grain: one row per (station_id, day_type, local_hour).
-- A station's daily rhythm over the whole year, for the station panel.
with trips as (
    select * from {{ ref('stg_trips') }} where is_plausible and {{ starts_at_nyc_station() }}
),
days as (select local_date, day_type from {{ ref('fct_city_day') }})

select
    t.start_station_id as station_id,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    t.start_hour_local as local_hour,
    count(*) as trips
from trips t
join days d on d.local_date = t.start_date_local
group by 1, 2, 3
