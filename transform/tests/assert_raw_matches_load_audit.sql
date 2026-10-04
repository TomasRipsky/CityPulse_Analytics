-- Every loaded period holds exactly the rows its latest load wrote, and that load wrote exactly the
-- rows the lake manifest counted at the source. Fails on: a short or duplicated partition, a
-- partition with no audit row, an audit row with no partition.
with latest_load as (
    select source, period, expected_rows, loaded_rows
    from {{ source('raw', 'load_audit') }}
    qualify row_number() over (partition by source, period order by loaded_at desc) = 1
),

raw_rows as (
    select 'weather' as source, format_date('%F', local_date) as period, count(*) as rows_in_raw
    from {{ source('raw', 'weather_hourly') }} group by 2
    union all
    select 'air_quality', format_date('%F', local_date), count(*)
    from {{ source('raw', 'air_quality_hourly') }} group by 2
    union all
    select 'citibike', format_date('%Y-%m', source_month), count(*)
    from {{ source('raw', 'trips') }} group by 2
)

select *
from latest_load
full outer join raw_rows using (source, period)
where rows_in_raw is distinct from expected_rows
   or loaded_rows is distinct from expected_rows
