-- grain: one row per (month, day_type, local_hour, rider), local_hour null for daily baselines.
-- "Expected trips": the mean of the same month, kind of day (and hour) under dry conditions.
-- rider: all, member, casual. Cells need at least 3 dry periods to count as a baseline.
with hours as (
    select month, day_type, local_hour, trips, member_trips, casual_trips
    from {{ ref('fct_city_hour') }}
    where trips_loaded and is_dry
),

days as (
    select month, day_type, trips, member_trips, casual_trips
    from {{ ref('fct_city_day') }}
    where trips_loaded and is_dry
),

long_hours as (
    select month, day_type, local_hour, 'all' as rider, trips as n from hours
    union all select month, day_type, local_hour, 'member', member_trips from hours
    union all select month, day_type, local_hour, 'casual', casual_trips from hours
),

long_days as (
    select month, day_type, cast(null as int64) as local_hour, 'all' as rider, trips as n from days
    union all select month, day_type, null, 'member', member_trips from days
    union all select month, day_type, null, 'casual', casual_trips from days
)

select month, day_type, local_hour, rider, avg(n) as expected_trips, count(*) as dry_periods
from (select * from long_hours union all select * from long_days)
group by month, day_type, local_hour, rider
having count(*) >= 3
