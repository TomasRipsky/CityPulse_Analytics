
  
    

    create or replace table `project-6c4733db-2f24-496d-90f`.`citypulse_marts`.`daily_mobility_summary`
      
    
    

    OPTIONS()
    as (
      -- daily_mobility_summary.sql
-- Resumen diario de movilidad en Citibike NYC.
-- Una fila por día con métricas de uso agregadas desde los viajes individuales.

with daily as (
    select
        date(started_at)                        as date,
        year,
        month,

        -- Volumen
        count(*)                                as total_rides,
        count(distinct start_station_name)      as active_start_stations,
        count(distinct end_station_name)        as active_end_stations,

        -- Duración
        round(avg(duration_minutes), 2)         as duration_avg_min,
        round(min(duration_minutes), 2)         as duration_min_min,
        round(max(duration_minutes), 2)         as duration_max_min,

        -- Tipo de usuario
        countif(member_casual = 'member')       as rides_member,
        countif(member_casual = 'casual')       as rides_casual,
        round(
            countif(member_casual = 'member') * 100.0 / count(*), 2
        )                                       as pct_member,

        -- Tipo de bicicleta
        countif(rideable_type = 'electric_bike') as rides_electric,
        countif(rideable_type = 'classic_bike')  as rides_classic,
        round(
            countif(rideable_type = 'electric_bike') * 100.0 / count(*), 2
        )                                        as pct_electric

    from `project-6c4733db-2f24-496d-90f`.`citypulse_staging`.`stg_citibike`
    group by date(started_at), year, month
)

select * from daily
order by date desc
    );
  