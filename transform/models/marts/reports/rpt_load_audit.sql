-- grain: one row per (source, month).
-- Proof on the BI page that what the sources published is what the warehouse holds: per source and
-- month, the rows counted at the source (lake manifest) and the rows loaded, from each period's
-- latest load. assert_raw_matches_load_audit checks the partitions themselves.
with latest_load as (
    select source, period, expected_rows, loaded_rows, loaded_at
    from {{ source('raw', 'load_audit') }}
    qualify row_number() over (partition by source, period order by loaded_at desc) = 1
)

select
    source,
    date(cast(substr(period, 1, 4) as int64), cast(substr(period, 6, 2) as int64), 1) as month,
    count(*) as periods,
    sum(expected_rows) as source_rows,
    sum(loaded_rows) as loaded_rows,
    countif(expected_rows is distinct from loaded_rows) as mismatched_periods,
    format_timestamp('%F %R UTC', max(loaded_at)) as last_loaded_at
from latest_load
group by 1, 2
