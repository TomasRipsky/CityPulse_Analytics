-- daily_weather_summary.sql
-- Resumen diario de clima para NYC.
-- Una fila por día con las métricas agregadas desde los datos horarios.

with daily as (
    select
        date,
        location,

        -- Temperatura
        round(avg(temperature_c), 2)    as temp_avg_c,
        round(min(temperature_c), 2)    as temp_min_c,
        round(max(temperature_c), 2)    as temp_max_c,

        -- Precipitación — sumamos las horas para obtener el total del día
        round(sum(precipitation_mm), 2) as precipitation_total_mm,

        -- Viento
        round(avg(wind_speed_kmh), 2)   as wind_avg_kmh,
        round(max(wind_speed_kmh), 2)   as wind_max_kmh,

        -- Humedad
        round(avg(humidity_pct), 2)     as humidity_avg_pct

    from {{ ref('stg_weather') }}
    group by date, location
)

select * from daily
order by date desc