-- grain: one row per (station_id, month, day_type, rider).
-- Station demand for the BI page's map and ranking, filterable by month, kind of day and rider.
-- Trips that do not start at a New York station (e-bikes left outside a dock, a few demo stations
-- elsewhere) are not here; they are in rpt_day_riders, so totals still add up (tested).
with counts as (select * from {{ ref('int_trip_hour_counts') }} where station_id is not null),
days as (select local_date, month, day_type from {{ ref('fct_city_day') }} where trips_loaded)

select
    c.station_id,
    d.month,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    c.rider,
    sum(c.trips) as trips,
    sum(if(c.bike_type = 'electric', c.trips, 0)) as electric_trips,
    round(sum(c.minutes_total), 1) as minutes_total
from counts c
join days d using (local_date)
group by 1, 2, 3, 4
