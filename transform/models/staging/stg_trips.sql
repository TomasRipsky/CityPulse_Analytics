{{ config(materialized='table') }}
-- grain: one row per trip (ride_id).
-- A table, not a view: the de-duplication reads every trip once per build, and the tests and the
-- models below then read only the columns they need instead of re-running it.
-- A trip that starts on the last evening of a month can be published in two months' files: keep
-- the copy from the latest file. Adds New York day and hour, duration, and whether the trip is
-- plausible for analysis (1 min to 3 h; shorter ones are false starts, longer ones mostly bikes not
-- docked properly). Implausible trips are kept and flagged, never silently dropped.
with source as (
    select * from {{ source('raw', 'trips') }}
),

deduped as (
    select *
    from source
    qualify row_number() over (partition by ride_id order by source_month desc, source_file desc) = 1
)

select
    ride_id,
    rideable_type,
    member_casual,
    started_at,
    ended_at,
    timestamp_trunc(started_at, hour) as start_hour,
    date(started_at, '{{ var("timezone") }}') as start_date_local,
    extract(hour from datetime(started_at, '{{ var("timezone") }}')) as start_hour_local,
    timestamp_diff(ended_at, started_at, second) / 60 as duration_min,
    timestamp_diff(ended_at, started_at, second) between 60 and 3 * 3600 as is_plausible,
    start_station_id,
    start_station_name,
    end_station_id,
    end_station_name,
    start_lat,
    start_lng,
    end_lat,
    end_lng,
    source_month,
    source_file
from deduped
