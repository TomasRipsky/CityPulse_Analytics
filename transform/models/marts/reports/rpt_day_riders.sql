-- grain: one row per (local_date, rider, bike_type) with at least one plausible trip.
-- The BI page's demand and KPI base: trips and minutes ridden (a sum, so any filter can average
-- them), with the calendar to filter on. Holidays count as weekends, as everywhere in the effects.
with trips as (
    select * from {{ ref('stg_trips') }} where is_plausible
),
days as (select local_date, month, day_type from {{ ref('fct_city_day') }})

select
    t.start_date_local as local_date,
    d.month,
    if(d.day_type = 'workday', 'workday', 'weekend') as day_type,
    t.member_casual as rider,
    if(t.rideable_type = 'electric_bike', 'electric', 'classic') as bike_type,
    count(*) as trips,
    round(sum(t.duration_min), 1) as minutes_total
from trips t
join days d on d.local_date = t.start_date_local
group by 1, 2, 3, 4, 5
