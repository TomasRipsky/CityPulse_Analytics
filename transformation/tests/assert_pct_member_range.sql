-- assert_pct_member_range.sql
-- Verifica que el porcentaje de usuarios member esté siempre entre 0 y 100.
-- Un valor fuera de rango indica un error en el cálculo del modelo.

select
    date,
    pct_member
from {{ ref('daily_mobility_summary') }}
where pct_member < 0
   or pct_member > 100