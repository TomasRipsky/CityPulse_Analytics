{{ config(store_failures=true) }}
-- Each New York day has as many hourly readings as it has hours: 24, or 23 / 25 on the days the
-- clocks change. Checked for weather and air quality.
with readings as (
    select 'weather' as source, local_date from {{ ref('stg_weather_hourly') }}
    union all
    select 'air_quality', local_date from {{ ref('stg_air_quality_hourly') }}
),

per_day as (
    select source, local_date, count(*) as readings
    from readings
    group by source, local_date
)

select
    source,
    local_date,
    readings,
    timestamp_diff(
        timestamp(date_add(local_date, interval 1 day), '{{ var("timezone") }}'),
        timestamp(local_date, '{{ var("timezone") }}'),
        hour
    ) as hours_in_day
from per_day
where readings != timestamp_diff(
    timestamp(date_add(local_date, interval 1 day), '{{ var("timezone") }}'),
    timestamp(local_date, '{{ var("timezone") }}'),
    hour
)
