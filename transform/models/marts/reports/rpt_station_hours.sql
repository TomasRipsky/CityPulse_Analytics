-- grain: one row per (station_id, day_type, local_hour).
-- A station's daily rhythm over the whole year, for the station panel.
with counts as (select * from {{ ref('int_trip_hour_counts') }} where station_id is not null),
days as (select local_date, day_type from {{ ref('fct_city_day') }} where trips_loaded)

select
    c.station_id,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    c.local_hour,
    sum(c.trips) as trips
from counts c
join days d using (local_date)
group by 1, 2, 3
