-- The BI page's daily base adds up to the same trips as fct_city_day, every loaded day — and has
-- no day that fct_city_day does not count.
with bi as (
    select local_date, sum(trips) as trips from {{ ref('rpt_day_riders') }} group by 1
),
city as (
    select local_date, trips from {{ ref('fct_city_day') }} where trips_loaded
)

select local_date, city.trips as city_trips, bi.trips as bi_trips
from city
full outer join bi using (local_date)
where coalesce(bi.trips, 0) != coalesce(city.trips, 0)
