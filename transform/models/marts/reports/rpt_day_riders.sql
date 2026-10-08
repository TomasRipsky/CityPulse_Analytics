-- grain: one row per (local_date, rider, bike_type) with at least one plausible trip.
-- The BI page's demand and KPI base: trips and minutes ridden (a sum, so any filter can average
-- them), with the calendar to filter on. Holidays count as weekends, as everywhere in the effects.
-- Loaded months only: a month's file also holds a few trips from the evening before it began.
with counts as (select * from {{ ref('int_trip_hour_counts') }}),
days as (select local_date, month, day_type from {{ ref('fct_city_day') }} where trips_loaded)

select
    c.local_date,
    d.month,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    c.rider,
    c.bike_type,
    sum(c.trips) as trips,
    round(sum(c.minutes_total), 1) as minutes_total
from counts c
join days d using (local_date)
group by 1, 2, 3, 4, 5
