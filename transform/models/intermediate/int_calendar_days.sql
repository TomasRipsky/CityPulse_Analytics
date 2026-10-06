-- grain: one row per New York day from the first to the last day with weather data.
-- day_type: holiday (US federal, observed), weekend, or workday. trips_loaded says whether the
-- day's Citi Bike month is in the warehouse, so a day with no trips (an outage) is told apart from
-- a month that was never loaded.
with bounds as (
    select min(local_date) as first_day, max(local_date) as last_day
    from {{ ref('stg_weather_hourly') }}
),

days as (
    select day as local_date
    from bounds, unnest(generate_date_array(first_day, last_day)) as day
),

trip_months as (
    select distinct parse_date('%Y-%m', period) as month
    from {{ source('raw', 'load_audit') }}
    where source = 'citibike' and loaded_rows > 0
)

select
    d.local_date,
    format_date('%A', d.local_date) as weekday,
    extract(dayofweek from d.local_date) in (1, 7) as is_weekend,
    h.holiday,
    case
        when h.date is not null then 'holiday'
        when extract(dayofweek from d.local_date) in (1, 7) then 'weekend'
        else 'workday'
    end as day_type,
    date_trunc(d.local_date, month) as month,
    case
        when extract(month from d.local_date) in (12, 1, 2) then 'winter'
        when extract(month from d.local_date) in (3, 4, 5) then 'spring'
        when extract(month from d.local_date) in (6, 7, 8) then 'summer'
        else 'autumn'
    end as season,
    m.month is not null as trips_loaded
from days d
left join {{ ref('us_holidays') }} h on h.date = d.local_date
left join trip_months m on m.month = date_trunc(d.local_date, month)
