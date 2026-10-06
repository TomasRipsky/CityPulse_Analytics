{{ config(store_failures=true) }}
-- The holiday seed covers whole years; a calendar day outside them would be a "workday" even on
-- Christmas. Extend seeds/us_holidays.csv before loading another year.
select c.local_date
from {{ ref('int_calendar_days') }} c
where extract(year from c.local_date) not in (
    select distinct extract(year from date) from {{ ref('us_holidays') }}
)
