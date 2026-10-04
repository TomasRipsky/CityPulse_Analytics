-- grain: one row per (condition, band, rider).
-- How many more or fewer trips than expected under each condition. expected = the dry-conditions
-- mean for the same month and kind of day (and, for hourly conditions, the same hour); effect =
-- actual / expected − 1, summed over every period in the band. Rain is measured per hour (it comes
-- and goes); snow, wind and air quality per day.
with hours as (select * from {{ ref('fct_city_hour') }} where trips_loaded and precipitation_mm is not null),
days as (select * from {{ ref('fct_city_day') }} where trips_loaded),
baselines as (select * from {{ ref('int_baselines') }}),

hour_rows as (
    select
        'rain' as condition,
        case
            when snowfall_cm > 0 then null
            when precipitation_mm = 0 then 'dry'
            when precipitation_mm < 1 then 'drizzle (< 1 mm/h)'
            when precipitation_mm < 4 then 'rain (1–4 mm/h)'
            else 'heavy rain (≥ 4 mm/h)'
        end as band,
        case
            when precipitation_mm = 0 then 0
            when precipitation_mm < 1 then 1
            when precipitation_mm < 4 then 2
            else 3
        end as band_order,
        month, day_type, local_hour, trips, member_trips, casual_trips
    from hours
),

day_rows as (
    select 'snow' as condition,
        case when snowfall_cm = 0 then 'no snow' when snowfall_cm < 5 then 'light snow (< 5 cm)' else 'snowfall ≥ 5 cm' end as band,
        case when snowfall_cm = 0 then 0 when snowfall_cm < 5 then 1 else 2 end as band_order,
        month, day_type, cast(null as int64) as local_hour, trips, member_trips, casual_trips
    from days where snowfall_cm is not null
    union all
    select 'wind',
        case when wind_gusts_max_kmh < 30 then 'calm (gusts < 30 km/h)' when wind_gusts_max_kmh < 50 then 'breezy (30–50)' when wind_gusts_max_kmh < 70 then 'windy (50–70)' else 'gale (≥ 70)' end,
        case when wind_gusts_max_kmh < 30 then 0 when wind_gusts_max_kmh < 50 then 1 when wind_gusts_max_kmh < 70 then 2 else 3 end,
        month, day_type, null, trips, member_trips, casual_trips
    from days where is_dry and wind_gusts_max_kmh is not null
    union all
    select 'air quality', aqi_category,
        case aqi_category when 'good' then 0 when 'moderate' then 1 when 'unhealthy for sensitive groups' then 2 when 'unhealthy' then 3 when 'very unhealthy' then 4 else 5 end,
        month, day_type, null, trips, member_trips, casual_trips
    from days where is_dry and aqi_category is not null
),

periods as (
    select * from hour_rows where band is not null
    union all
    select * from day_rows
),

long as (
    select condition, band, band_order, month, day_type, local_hour, 'all' as rider, trips as actual from periods
    union all select condition, band, band_order, month, day_type, local_hour, 'member', member_trips from periods
    union all select condition, band, band_order, month, day_type, local_hour, 'casual', casual_trips from periods
)

select
    l.condition,
    l.band,
    l.band_order,
    l.rider,
    count(*) as periods,
    sum(l.actual) as trips,
    round(sum(b.expected_trips)) as expected_trips,
    round(100 * (safe_divide(sum(l.actual), sum(b.expected_trips)) - 1), 1) as effect_pct
from long l
join baselines b
    on b.month = l.month
    and b.day_type = l.day_type
    and b.rider = l.rider
    and b.local_hour is not distinct from l.local_hour
group by l.condition, l.band, l.band_order, l.rider
