{{ config(store_failures=true) }}
-- Every day with trip data has its weather and air quality: a missing day would silently drop out
-- of every comparison.
select local_date, temperature_mean_c, aqi_mean
from {{ ref('fct_city_day') }}
where trips_loaded and (temperature_mean_c is null or aqi_mean is null)
