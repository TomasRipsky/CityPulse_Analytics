-- Station months plus the trips that do not start at a New York station equal the BI daily base,
-- every month: the map and ranking lose no other trips.
with stations as (
    select month, sum(trips) as trips from {{ ref('rpt_station_months') }} group by 1
),
days as (
    select month, sum(trips) as trips from {{ ref('rpt_day_riders') }} group by 1
),
unstationed as (
    select d.month, sum(c.trips) as trips
    from {{ ref('int_trip_hour_counts') }} c
    join {{ ref('fct_city_day') }} d using (local_date)
    where c.station_id is null and d.trips_loaded
    group by 1
)

select d.month, d.trips as day_trips, s.trips as station_trips, u.trips as unstationed_trips
from days d
left join stations s using (month)
left join unstationed u using (month)
where coalesce(s.trips, 0) + coalesce(u.trips, 0) != d.trips
