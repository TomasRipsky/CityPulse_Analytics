-- monthly_city_pulse.sql
-- Mart de correlación mensual — el corazón analítico de CityPulse.
--
-- Une clima, calidad del aire y movilidad a nivel mensual para responder
-- preguntas de negocio sobre cómo el entorno urbano afecta el comportamiento
-- de los ciudadanos en Nueva York.
--
-- Preguntas que responde este modelo:
--   1. ¿Los meses más fríos tienen menos viajes en bici?
--   2. ¿La lluvia acumulada mensual reduce el uso de Citibike?
--   3. ¿El viento fuerte desplaza usuarios casual hacia member?
--   4. ¿La mala calidad del aire reduce los viajes o cambia el tipo de usuario?
--   5. ¿Los meses con más horas de AQI bueno tienen más viajes casuales?
--   6. ¿La duración media de los viajes aumenta cuando hace buen tiempo?
--   7. ¿Las bicis eléctricas se usan más en condiciones adversas?
--   8. ¿Hay un umbral de temperatura por encima del cual el uso se dispara?

with weather_monthly as (
    -- Agregamos los resúmenes diarios de clima a nivel mensual
    select
        extract(year from date)  as year,
        extract(month from date) as month,

        -- Temperatura mensual
        round(avg(temp_avg_c), 2)           as temp_avg_c,
        round(min(temp_min_c), 2)           as temp_min_c,
        round(max(temp_max_c), 2)           as temp_max_c,
        round(stddev(temp_avg_c), 2)        as temp_stddev_c,       -- variabilidad térmica del mes

        -- Precipitación mensual
        round(sum(precipitation_total_mm), 2) as precipitation_total_mm,
        countif(precipitation_total_mm > 0)   as rainy_days,        -- días con lluvia
        countif(precipitation_total_mm > 10)  as heavy_rain_days,   -- días con lluvia intensa

        -- Viento mensual
        round(avg(wind_avg_kmh), 2)         as wind_avg_kmh,
        round(max(wind_max_kmh), 2)         as wind_max_kmh,
        countif(wind_max_kmh > 30)          as windy_days,          -- días con viento fuerte

        -- Humedad mensual
        round(avg(humidity_avg_pct), 2)     as humidity_avg_pct,

        -- Clasificación climática del mes — útil para segmentar en Looker
        case
            when avg(temp_avg_c) < 0  then 'Freezing'
            when avg(temp_avg_c) < 10 then 'Cold'
            when avg(temp_avg_c) < 20 then 'Mild'
            when avg(temp_avg_c) < 28 then 'Warm'
            else 'Hot'
        end as weather_category

    from {{ ref('daily_weather_summary') }}
    group by year, month
),

air_quality_monthly as (
    -- Agregamos los resúmenes diarios de calidad del aire a nivel mensual
    select
        extract(year from date)  as year,
        extract(month from date) as month,

        -- AQI mensual
        round(avg(aqi_avg), 0)              as aqi_avg,
        max(aqi_max)                        as aqi_max,

        -- Contaminantes
        round(avg(pm2_5_avg), 2)            as pm2_5_avg,
        round(avg(pm10_avg), 2)             as pm10_avg,
        round(avg(ozone_avg), 2)            as ozone_avg,

        -- Distribución de calidad del aire — total de horas en el mes por categoría
        sum(hours_good)                     as hours_good,
        sum(hours_moderate)                 as hours_moderate,
        sum(hours_unhealthy_sensitive)      as hours_unhealthy_sensitive,
        sum(hours_unhealthy)                as hours_unhealthy,
        sum(hours_very_unhealthy)           as hours_very_unhealthy,

        -- % del mes con aire de buena calidad
        round(
            sum(hours_good) * 100.0 /
            nullif(sum(hours_good + hours_moderate + hours_unhealthy_sensitive
                       + hours_unhealthy + hours_very_unhealthy), 0)
        , 2) as pct_hours_good_air,

        -- Días con AQI medio "aceptable" (≤ 100)
        countif(aqi_avg <= 100)             as days_acceptable_aqi,

        -- Clasificación de calidad del aire del mes
        case
            when avg(aqi_avg) <= 50  then 'Good'
            when avg(aqi_avg) <= 100 then 'Moderate'
            when avg(aqi_avg) <= 150 then 'Unhealthy for Sensitive Groups'
            else 'Unhealthy'
        end as air_quality_category

    from {{ ref('daily_air_quality_summary') }}
    group by year, month
),

mobility_monthly as (
    -- Consolidamos la movilidad a nivel mensual
    -- (daily_mobility_summary ya es prácticamente mensual por la fuente Citibike)
    select
        year,
        month,

        sum(total_rides)                        as total_rides,
        round(avg(duration_avg_min), 2)         as duration_avg_min,
        sum(rides_member)                       as rides_member,
        sum(rides_casual)                       as rides_casual,
        round(
            sum(rides_member) * 100.0 / nullif(sum(total_rides), 0)
        , 2)                                    as pct_member,
        sum(rides_electric)                     as rides_electric,
        sum(rides_classic)                      as rides_classic,
        round(
            sum(rides_electric) * 100.0 / nullif(sum(total_rides), 0)
        , 2)                                    as pct_electric,
        round(avg(active_start_stations), 0)    as avg_active_stations

    from {{ ref('daily_mobility_summary') }}
    group by year, month
),

joined as (
    -- JOIN central: mobility como tabla base (es la que determina los meses disponibles)
    -- LEFT JOIN con clima y aire para no perder meses de Citibike si falta algún día
    select
        m.year,
        m.month,
        date(m.year, m.month, 1)                as month_date,  -- fecha para ordenar y filtrar en Looker

        -- ── MOVILIDAD ──────────────────────────────────────────
        m.total_rides,
        m.duration_avg_min,
        m.rides_member,
        m.rides_casual,
        m.pct_member,
        m.rides_electric,
        m.rides_classic,
        m.pct_electric,
        m.avg_active_stations,

        -- ── CLIMA ──────────────────────────────────────────────
        w.temp_avg_c,
        w.temp_min_c,
        w.temp_max_c,
        w.temp_stddev_c,
        w.precipitation_total_mm,
        w.rainy_days,
        w.heavy_rain_days,
        w.wind_avg_kmh,
        w.wind_max_kmh,
        w.windy_days,
        w.humidity_avg_pct,
        w.weather_category,

        -- ── CALIDAD DEL AIRE ───────────────────────────────────
        a.aqi_avg,
        a.aqi_max,
        a.pm2_5_avg,
        a.pm10_avg,
        a.ozone_avg,
        a.pct_hours_good_air,
        a.days_acceptable_aqi,
        a.air_quality_category,

        -- ── MÉTRICAS DE CORRELACIÓN DERIVADAS ─────────────────
        -- Viajes por día del mes — normaliza meses con distinto número de días
        round(
            m.total_rides / nullif(extract(day from last_day(date(m.year, m.month, 1))), 0)
        , 0)                                    as rides_per_day,

        -- Ratio viajes casual / temperatura — sube con el buen tiempo?
        round(m.rides_casual / nullif(w.temp_avg_c, 0), 0) as casual_rides_per_degree,

        -- Impacto lluvia: viajes por mm de precipitación
        round(
            m.total_rides / nullif(w.precipitation_total_mm, 0)
        , 0)                                    as rides_per_mm_rain,

        -- Condiciones generales del mes — resumen ejecutivo
        case
            when w.temp_avg_c >= 15
             and w.precipitation_total_mm < 80
             and a.aqi_avg <= 100
            then 'Favorable'
            when w.temp_avg_c < 5
              or w.precipitation_total_mm > 150
              or a.aqi_avg > 150
            then 'Adverse'
            else 'Neutral'
        end                                     as conditions_category

    from mobility_monthly m
    left join weather_monthly   w on m.year = w.year and m.month = w.month
    left join air_quality_monthly a on m.year = a.year and m.month = a.month
)

select * from joined
order by year desc, month desc
