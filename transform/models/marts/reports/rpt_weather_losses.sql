-- grain: one row per (month, condition, band, rider), reference bands excluded.
-- Trips lost (or gained) to the weather: expected − actual over the band's periods in the month,
-- from the same per-period comparison as the effects. Conditions overlap (a snowy day's hours can
-- also be rainy hours), so losses must never be summed across conditions.
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
where not is_reference
group by 1, 2, 3, 4, 5
