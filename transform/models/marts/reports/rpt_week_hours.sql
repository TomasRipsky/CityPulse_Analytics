-- grain: one row per (month, weekday, day_type, local_hour, rider).
-- The weekday × hour heatmap: trips summed over the month's days of that weekday and kind
-- (holidays are weekends, so a holiday Monday does not dilute workday Mondays), and how many of
-- those days had that hour — so the page averages correctly for any month range, including the
-- spring-forward Sunday with no 02:00 (the fall-back day's two 01:00 hours add to one).
with hours as (
    select h.local_date, h.local_hour, h.member_trips, h.casual_trips, d.month, d.weekday,
        extract(dayofweek from h.local_date) as weekday_number,
        if(d.day_type = 'workday', 'workday', 'weekend') as day_type
    from {{ ref('fct_city_hour') }} h
    join {{ ref('fct_city_day') }} d using (local_date)
    where d.trips_loaded
),

long as (
    select month, weekday, weekday_number, day_type, local_hour, local_date, 'member' as rider, member_trips as trips
    from hours
    union all
    select month, weekday, weekday_number, day_type, local_hour, local_date, 'casual', casual_trips
    from hours
)

select
    month,
    weekday,
    weekday_number,
    day_type,
    local_hour,
    rider,
    sum(trips) as trips,
    count(distinct local_date) as days
from long
group by 1, 2, 3, 4, 5, 6
