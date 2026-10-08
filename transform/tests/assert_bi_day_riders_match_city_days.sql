-- The BI page's daily base adds up to the same trips as fct_city_day, every loaded day.
with bi as (
    select local_date, sum(trips) as trips from {{ ref('rpt_day_riders') }} group by 1
)

select d.local_date, d.trips as city_trips, bi.trips as bi_trips
from {{ ref('fct_city_day') }} d
left join bi using (local_date)
where d.trips_loaded and coalesce(bi.trips, 0) != d.trips
