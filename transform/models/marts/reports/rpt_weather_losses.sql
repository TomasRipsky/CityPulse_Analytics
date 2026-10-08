-- grain: one row per (month, condition, band, rider) for rain (per hour) and snow (per day),
-- reference bands excluded; rider is member or casual (their sum is everyone).
-- Trips lost (or gained) to the weather: expected − actual over the band's periods in the month,
-- from the same per-period comparison as the effects. Rain and snow overlap (a snowy day's hours
-- can also be rainy hours), so their losses must never be added together. Wind and air quality are
-- measured on dry days only — their "losses" would leave out the stormy days — so they are not
-- here. Periods without a baseline (fewer than 3 reference periods) are not counted.
select
    month,
    condition,
    band,
    band_order,
    rider,
    count(*) as periods,
    sum(trips) as trips,
    round(sum(expected_trips)) as expected_trips,
    round(sum(expected_trips) - sum(trips)) as trips_lost
from {{ ref('fct_condition_periods') }}
where not is_reference and condition in ('rain', 'snow') and rider in ('member', 'casual')
group by 1, 2, 3, 4, 5
