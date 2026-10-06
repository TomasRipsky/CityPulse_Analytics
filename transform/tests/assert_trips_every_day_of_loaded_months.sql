{{ config(store_failures=true) }}
-- Citi Bike runs every day: a day in a loaded month with no trips means data went missing —
-- unless a known closure covers it (seeds/known_service_closures.csv, with its source).
select local_date, trips
from {{ ref('fct_city_day') }}
where trips_loaded and trips = 0 and not service_closed
