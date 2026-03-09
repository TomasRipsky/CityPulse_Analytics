-- assert_air_quality_complete_hours.sql
-- Verifica que ningún día tenga menos de 20 horas de datos de calidad del aire.
-- Similar al test de clima — detecta extracciones incompletas.

select
    date,
    count(*) as hours_count
from {{ ref('stg_air_quality') }}
group by date
having count(*) < 20