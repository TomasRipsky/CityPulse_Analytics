-- The heatmap's trips add up to fct_city_day's, month by month.
with heat as (
    select month, sum(trips) as trips from {{ ref('rpt_week_hours') }} group by 1
),
city as (
    select month, sum(trips) as trips from {{ ref('fct_city_day') }} where trips_loaded group by 1
)

select month, city.trips as city_trips, heat.trips as heat_trips
from city
full outer join heat using (month)
where coalesce(heat.trips, 0) != coalesce(city.trips, 0)
