-- daily_air_quality_summary.sql
-- Resumen diario de calidad del aire para NYC.
-- Una fila por día con métricas agregadas y distribución de categorías AQI.

with daily as (
    select
        date,
        location,

        -- Métricas principales
        round(avg(pm2_5), 2)    as pm2_5_avg,
        round(max(pm2_5), 2)    as pm2_5_max,
        round(avg(pm10), 2)     as pm10_avg,
        round(avg(ozone), 2)    as ozone_avg,
        round(avg(us_aqi), 0)   as aqi_avg,
        max(us_aqi)             as aqi_max,

        -- Categoría dominante del día — la que más horas ocupa
        approx_top_count(aqi_category, 1)[offset(0)].value as aqi_dominant_category,

        -- Horas en cada categoría — útil para el dashboard
        countif(aqi_category = 'Good')                          as hours_good,
        countif(aqi_category = 'Moderate')                      as hours_moderate,
        countif(aqi_category = 'Unhealthy for Sensitive Groups') as hours_unhealthy_sensitive,
        countif(aqi_category = 'Unhealthy')                     as hours_unhealthy,
        countif(aqi_category = 'Very Unhealthy')                as hours_very_unhealthy,
        countif(aqi_category = 'Hazardous')                     as hours_hazardous

    from {{ ref('stg_air_quality') }}
    group by date, location
)

select * from daily
order by date desc
