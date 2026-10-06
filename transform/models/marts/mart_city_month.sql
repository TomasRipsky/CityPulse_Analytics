-- grain: one row per month (first day of the month, New York calendar).
-- A summary for dashboards: totals and averages only, no derived ratios between units.
with days as (select * from {{ ref('fct_city_day') }})

select
    month,
    count(*) as days,
    countif(trips_loaded) as days_with_trip_data,
    sum(trips) as trips,
    round(avg(trips)) as trips_per_day,
    round(100 * safe_divide(sum(member_trips), sum(trips)), 1) as member_share_pct,
    round(100 * safe_divide(sum(electric_trips), sum(trips)), 1) as electric_share_pct,
    round(avg(temperature_mean_c), 1) as temperature_mean_c,
    round(sum(precipitation_mm), 1) as precipitation_mm,
    countif(precipitation_mm >= 1) as wet_days,
    countif(snowfall_cm > 0) as snow_days,
    round(avg(aqi_mean)) as aqi_mean
from days
group by month
