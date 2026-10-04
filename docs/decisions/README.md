# Decisions

Architecture decision records. 0001–0007 were written retroactively on 2026-10-04: they record
the decisions taken when the project was built (6–10 March 2026), as the code shows them, plus a
**Revisited** note with what the [2026-10 audit](../audit/2026-10-04-audit.md) found. Records are
never rewritten; a changed decision gets a new record that supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-open-data-sources-for-nyc.md) | Open-Meteo and Citi Bike open data for New York | Accepted |
| [0002](0002-medallion-lake-in-one-gcs-bucket.md) | Medallion lake in one GCS bucket, Hive-style paths | Accepted |
| [0003](0003-airflow-on-a-free-tier-vm.md) | Airflow on a free-tier e2-micro VM, not Cloud Composer | Accepted |
| [0004](0004-idempotent-delete-then-append-loads.md) | Idempotent loads: delete the period, then append | Accepted |
| [0005](0005-workload-identity-federation-for-ci.md) | Workload Identity Federation for GitHub Actions | Accepted |
| [0006](0006-dbt-staging-views-and-mart-tables.md) | dbt: staging views and mart tables in separate datasets | Accepted |
| [0007](0007-citibike-monthly-with-two-month-lag.md) | Citi Bike loaded monthly, two months behind | Accepted |
