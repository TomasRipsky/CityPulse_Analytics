{{ config(materialized='table') }}
-- grain: one row per (reference, month, day_type, local_hour, rider); local_hour null for days.
-- "Expected trips": the mean of the REFERENCE periods of each condition, for the same month and
-- kind of day (and, for rain, the same hour). Each condition is compared with good conditions of
-- its own kind, never with a set that includes the periods being measured:
--   dry hour       rain (hourly): no precipitation, no snow in the hour
--   dry day        snow: under 1 mm of precipitation and no snow over the day
--   calm dry day   wind: a dry day whose strongest gust stayed under 40 km/h
--   clean dry day  air quality: a dry day with "good" air (mean AQI ≤ 50)
-- Holidays count as weekends (a month has at most two, too few for a baseline of their own).
-- rider: all, member, casual. A baseline needs at least 3 reference periods.
with hours as (
    select month, day_type, local_hour, trips, member_trips, casual_trips
    from {{ ref('fct_city_hour') }}
    where trips_loaded and is_dry
),

days as (
    select month, day_type, trips, member_trips, casual_trips, wind_gusts_max_kmh, aqi_category
    from {{ ref('fct_city_day') }}
    where trips_loaded and is_dry
),

reference_periods as (
    select 'dry hour' as reference, month, day_type, local_hour, trips, member_trips, casual_trips
    from hours
    union all
    select 'dry day', month, day_type, null, trips, member_trips, casual_trips
    from days
    union all
    select 'calm dry day', month, day_type, null, trips, member_trips, casual_trips
    from days where wind_gusts_max_kmh < 40
    union all
    select 'clean dry day', month, day_type, null, trips, member_trips, casual_trips
    from days where aqi_category = 'good'
),

long as (
    select reference, month, if(day_type = 'holiday', 'weekend', day_type) as day_type, local_hour,
        'all' as rider, trips as n
    from reference_periods
    union all
    select reference, month, if(day_type = 'holiday', 'weekend', day_type), local_hour, 'member', member_trips
    from reference_periods
    union all
    select reference, month, if(day_type = 'holiday', 'weekend', day_type), local_hour, 'casual', casual_trips
    from reference_periods
)

select
    reference,
    month,
    day_type,
    cast(local_hour as int64) as local_hour,
    rider,
    avg(n) as expected_trips,
    count(*) as reference_periods
from long
group by reference, month, day_type, local_hour, rider
having count(*) >= 3
