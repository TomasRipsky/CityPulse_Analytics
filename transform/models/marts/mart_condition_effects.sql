-- grain: one row per (condition, band, rider).
-- How many more or fewer trips than in good conditions: effect = sum(actual) / sum(expected) − 1
-- over every period of the band (see fct_condition_periods for how each period's expected trips
-- are set). The reference band itself is listed (is_reference) as a check: its effect is ~0.
select
    condition,
    band,
    band_order,
    is_reference,
    rider,
    count(*) as periods,
    sum(trips) as trips,
    round(sum(expected_trips)) as expected_trips,
    round(100 * (safe_divide(sum(trips), sum(expected_trips)) - 1), 1) as effect_pct
from {{ ref('fct_condition_periods') }}
group by condition, band, band_order, is_reference, rider
