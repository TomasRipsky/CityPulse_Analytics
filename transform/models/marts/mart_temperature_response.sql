-- grain: one row per rider (all, member, casual).
-- What temperature itself does, with the season held still: on dry workdays and weekends, compare
-- each day with its own month and kind of day. pct_per_degree is the least-squares slope of
-- (trips / that month's dry-day mean − 1) against (temperature − that month's dry-day mean), ×100:
-- "a day 1 °C warmer than usual for its month has this many % more trips".
with days as (
    select * from {{ ref('fct_city_day') }}
    where trips_loaded and not service_closed and is_dry and apparent_temperature_mean_c is not null and day_type != 'holiday'
),

long as (
    select month, day_type, apparent_temperature_mean_c as temp, 'all' as rider, trips as n from days
    union all select month, day_type, apparent_temperature_mean_c, 'member', member_trips from days
    union all select month, day_type, apparent_temperature_mean_c, 'casual', casual_trips from days
),

anomalies as (
    select
        rider,
        temp - avg(temp) over cell as temp_anomaly_c,
        safe_divide(n, avg(n) over cell) - 1 as trips_anomaly
    from long
    window cell as (partition by month, day_type, rider)
)

select
    rider,
    count(*) as days,
    round(100 * covar_samp(temp_anomaly_c, trips_anomaly) / nullif(var_samp(temp_anomaly_c), 0), 2) as pct_per_degree,
    round(corr(temp_anomaly_c, trips_anomaly), 2) as correlation
from anomalies
group by rider
