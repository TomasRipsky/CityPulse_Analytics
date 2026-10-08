-- Station months plus the trips that do not start at a New York station equal the BI daily base,
-- every month: the map and ranking lose no other trips.
with stations as (
    select month, sum(trips) as trips from {{ ref('rpt_station_months') }} group by 1
),
days as (
    select month, sum(trips) as trips from {{ ref('rpt_day_riders') }} group by 1
),
unstationed as (
    select date_trunc(start_date_local, month) as month, count(*) as trips
    from {{ ref('stg_trips') }}
    where is_plausible and not ({{ starts_at_nyc_station() }})
    group by 1
)

select d.month, d.trips as day_trips, s.trips as station_trips, u.trips as unstationed_trips
from days d
left join stations s using (month)
left join unstationed u using (month)
where coalesce(s.trips, 0) + coalesce(u.trips, 0) != d.trips
