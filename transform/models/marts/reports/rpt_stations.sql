-- grain: one row per start station (station_id).
-- Name and position (the median of trip starts: e-bike GPS fixes scatter, the median does not),
-- the year's trips and shares, and the station's own rain effect: its trips in rain hours against
-- the mean of its own dry hours with the same month, kind of day and hour (at least 3 of them),
-- counted only in months the station was active. Few stations see enough rain for that to mean
-- much: rain_effect_pct is set only where at least 200 trips were expected in rain hours.
with trips as (
    select * from {{ ref('stg_trips') }} where is_plausible and {{ starts_at_nyc_station() }}
),

stations as (
    select
        start_station_id as station_id,
        approx_top_count(start_station_name, 1)[offset(0)].value as station_name,
        approx_quantiles(start_lat, 2)[offset(1)] as lat,
        approx_quantiles(start_lng, 2)[offset(1)] as lng,
        count(*) as trips,
        round(100 * countif(member_casual = 'member') / count(*), 1) as member_share_pct,
        round(100 * countif(rideable_type = 'electric_bike') / count(*), 1) as electric_share_pct
    from trips
    group by 1
),

-- hours that can be compared: loaded, system open, no snow; rain = any precipitation
hours as (
    select hour_start, month, if(day_type = 'workday', 'workday', 'weekend') as day_type, local_hour,
        precipitation_mm > 0 as is_rain
    from {{ ref('fct_city_hour') }}
    where trips_loaded and not service_closed and precipitation_mm is not null
      and coalesce(snowfall_cm, 0) = 0
),

active_months as (
    select distinct start_station_id as station_id, date_trunc(start_date_local, month) as month
    from trips
),

station_hour_trips as (
    select start_station_id as station_id, start_hour as hour_start, count(*) as n
    from trips
    group by 1, 2
),

-- every comparable hour of every active station month, with zeros where nobody started a trip
grid as (
    select a.station_id, h.hour_start, h.month, h.day_type, h.local_hour, h.is_rain,
        coalesce(s.n, 0) as n
    from active_months a
    join hours h using (month)
    left join station_hour_trips s using (station_id, hour_start)
),

baseline as (
    select station_id, month, day_type, local_hour, avg(n) as expected
    from grid
    where not is_rain
    group by 1, 2, 3, 4
    having count(*) >= 3
),

rain as (
    select g.station_id, count(*) as rain_hours, sum(g.n) as rain_trips,
        sum(b.expected) as rain_expected_trips
    from grid g
    join baseline b using (station_id, month, day_type, local_hour)
    where g.is_rain
    group by 1
)

select
    s.*,
    r.rain_hours,
    r.rain_trips,
    round(r.rain_expected_trips) as rain_expected_trips,
    if(r.rain_expected_trips >= 200,
       round(100 * (r.rain_trips / r.rain_expected_trips - 1), 1), null) as rain_effect_pct
from stations s
left join rain r using (station_id)
