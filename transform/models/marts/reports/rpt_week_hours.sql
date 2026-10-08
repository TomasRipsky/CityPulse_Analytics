-- grain: one row per (month, weekday, local_hour, rider).
-- The weekday × hour heatmap: trips summed over the month's days of that weekday, and how many
-- such days there were, so the page shows trips per hour as a true average for any month range.
-- New York hours: on the fall-back day the repeated 01:00 hour adds to 01:00.
with hours as (
    select local_date, local_hour, member_trips, casual_trips
    from {{ ref('fct_city_hour') }}
    where trips_loaded
),
days as (
    select local_date, month, weekday, extract(dayofweek from local_date) as weekday_number
    from {{ ref('fct_city_day') }}
    where trips_loaded
),
day_counts as (
    select month, weekday_number, count(*) as days from days group by 1, 2
),
long as (
    select d.month, d.weekday, d.weekday_number, h.local_hour, 'member' as rider, h.member_trips as trips
    from hours h join days d using (local_date)
    union all
    select d.month, d.weekday, d.weekday_number, h.local_hour, 'casual', h.casual_trips
    from hours h join days d using (local_date)
)

select
    l.month,
    l.weekday,
    l.weekday_number,
    l.local_hour,
    l.rider,
    sum(l.trips) as trips,
    any_value(c.days) as days
from long l
join day_counts c using (month, weekday_number)
group by 1, 2, 3, 4, 5
