-- assert_weather_complete_hours.sql
-- Verifica que ningún día tenga menos de 20 horas de datos de clima.
-- Un día con menos de 20 horas indica una extracción incompleta de la API.
-- El test falla si encuentra días con datos insuficientes.

select
    date,
    count(*) as hours_count
from {{ ref('stg_weather') }}
group by date
having count(*) < 20