-- grain: one row per (temperature band, day_type).
-- Trips per day on dry days by how warm it felt (daily mean apparent temperature, 5 °C bands).
-- This is the raw seasonal curve: warmth comes with longer days, holidays and tourists, so it
-- shows how much more the city rides in warm weather, not what temperature alone causes
-- (see mart_temperature_response for that).
with days as (
    select * from {{ ref('fct_city_day') }}
    where trips_loaded and is_dry and apparent_temperature_mean_c is not null and day_type != 'holiday'
)

select
    cast(floor(apparent_temperature_mean_c / 5) * 5 as int64) as band_from_c,
    cast(floor(apparent_temperature_mean_c / 5) * 5 + 5 as int64) as band_to_c,
    day_type,
    count(*) as days,
    round(avg(trips)) as trips_per_day,
    round(100 * safe_divide(sum(casual_trips), sum(trips)), 1) as casual_share_pct
from days
group by 1, 2, 3
