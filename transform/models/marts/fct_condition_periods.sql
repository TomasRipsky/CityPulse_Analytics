{{ config(materialized='table') }}
-- grain: one row per (condition, period, rider) — a period is an hour for rain (hour_start), a New
-- York day for snow, wind and air quality (hour_start null).
-- Each period's actual trips next to what good conditions predict for it: the mean of its
-- condition's reference periods (see mart_baselines) for the same month and kind of day — and, for
-- rain, the same hour. Rain is measured per hour (it comes and goes); snow, wind and air quality per
-- day, on dry days for wind and air. Reference periods are listed too (is_reference): summed, their
-- actual and expected match by construction. Periods without a baseline (fewer than 3 reference
-- periods) are left out. mart_condition_effects and rpt_weather_losses aggregate this.
with hours as (
    select * from {{ ref('fct_city_hour') }}
    where trips_loaded and not service_closed and precipitation_mm is not null and coalesce(snowfall_cm, 0) = 0
),

days as (select * from {{ ref('fct_city_day') }} where trips_loaded and not service_closed),
baselines as (select * from {{ ref('mart_baselines') }}),

periods as (
    select
        'rain' as condition, 'dry hour' as reference,
        case
            when precipitation_mm = 0 then 'dry (reference)'
            when precipitation_mm < 1 then 'drizzle (< 1 mm/h)'
            when precipitation_mm < 4 then 'rain (1–4 mm/h)'
            else 'heavy rain (≥ 4 mm/h)'
        end as band,
        case when precipitation_mm = 0 then 0 when precipitation_mm < 1 then 1 when precipitation_mm < 4 then 2 else 3 end as band_order,
        local_date, hour_start, month, day_type, local_hour, trips, member_trips, casual_trips
    from hours
    union all
    select
        'snow', 'dry day',
        case when snowfall_cm = 0 then 'dry (reference)' when snowfall_cm < 5 then 'light snow (< 5 cm)' else 'snowfall ≥ 5 cm' end,
        case when snowfall_cm = 0 then 0 when snowfall_cm < 5 then 1 else 2 end,
        local_date, cast(null as timestamp), month, day_type, cast(null as int64), trips, member_trips, casual_trips
    from days
    where snowfall_cm > 0 or is_dry
    union all
    select
        'wind', 'calm dry day',
        case
            when wind_gusts_max_kmh < 40 then 'calm (reference, gusts < 40 km/h)'
            when wind_gusts_max_kmh < 55 then 'breezy (40–55 km/h)'
            when wind_gusts_max_kmh < 70 then 'windy (55–70 km/h)'
            else 'gale (≥ 70 km/h)'
        end,
        case when wind_gusts_max_kmh < 40 then 0 when wind_gusts_max_kmh < 55 then 1 when wind_gusts_max_kmh < 70 then 2 else 3 end,
        local_date, null, month, day_type, null, trips, member_trips, casual_trips
    from days
    where is_dry and wind_gusts_max_kmh is not null
    union all
    select
        'air quality', 'clean dry day',
        if(aqi_category = 'good', 'good (reference)', aqi_category),
        case aqi_category
            when 'good' then 0 when 'moderate' then 1 when 'unhealthy for sensitive groups' then 2
            when 'unhealthy' then 3 when 'very unhealthy' then 4 else 5
        end,
        local_date, null, month, day_type, null, trips, member_trips, casual_trips
    from days
    where is_dry and aqi_category is not null
),

long as (
    select condition, reference, band, band_order, local_date, hour_start, month, if(day_type = 'holiday', 'weekend', day_type) as day_type,
        local_hour, 'all' as rider, trips as actual
    from periods
    union all
    select condition, reference, band, band_order, local_date, hour_start, month, if(day_type = 'holiday', 'weekend', day_type),
        local_hour, 'member', member_trips
    from periods
    union all
    select condition, reference, band, band_order, local_date, hour_start, month, if(day_type = 'holiday', 'weekend', day_type),
        local_hour, 'casual', casual_trips
    from periods
)

select
    l.condition,
    l.band,
    l.band_order,
    l.band_order = 0 as is_reference,
    l.local_date,
    l.hour_start,
    l.month,
    l.day_type,
    l.local_hour,
    l.rider,
    l.actual as trips,
    b.expected_trips
from long l
join baselines b
    on b.reference = l.reference
    and b.month = l.month
    and b.day_type = l.day_type
    and b.rider = l.rider
    and b.local_hour is not distinct from l.local_hour
