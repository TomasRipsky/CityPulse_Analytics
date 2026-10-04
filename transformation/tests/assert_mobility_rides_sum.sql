-- assert_mobility_rides_sum.sql
-- Verifica que member + casual = total_rides en daily_mobility_summary.
-- Una discrepancia indica un problema en la lógica de agregación del modelo.

select
    date,
    total_rides,
    rides_member,
    rides_casual,
    rides_member + rides_casual as sum_check
from {{ ref('daily_mobility_summary') }}
where total_rides != rides_member + rides_casual
