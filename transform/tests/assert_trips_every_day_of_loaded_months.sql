-- Citi Bike runs every day: a day in a loaded month with no trips means data went missing.
select local_date, trips
from {{ ref('fct_city_day') }}
where trips_loaded and trips = 0
