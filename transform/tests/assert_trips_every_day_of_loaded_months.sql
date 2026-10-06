{{ config(store_failures=true) }}
-- Citi Bike runs every day: a day in a loaded month with no trips means data went missing —
-- unless the system was shut down that day (seeds/known_service_closures.csv, with its source).
select d.local_date, d.trips
from {{ ref('fct_city_day') }} d
left join {{ ref('known_service_closures') }} c on c.date = d.local_date
where d.trips_loaded and d.trips = 0 and c.date is null
