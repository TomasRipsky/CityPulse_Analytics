# Decisions

Architecture decision records: one page per durable decision — context, decision, alternatives,
consequences. Records are not rewritten; a changed decision gets a new record that supersedes the
old one. 0001–0007 were written retroactively and describe the March 2026 build (version 1).

| # | Decision | Status |
|---|---|---|
| [0001](0001-open-data-sources-for-nyc.md) | Open-Meteo and Citi Bike open data for New York | Accepted |
| [0002](0002-medallion-lake-in-one-gcs-bucket.md) | Medallion lake in one GCS bucket, Hive-style paths | Superseded by 0008 |
| [0003](0003-airflow-on-a-free-tier-vm.md) | Airflow on a free-tier e2-micro VM, not Cloud Composer | Superseded by 0017 |
| [0004](0004-idempotent-delete-then-append-loads.md) | Idempotent loads: delete the period, then append | Superseded by 0013 |
| [0005](0005-workload-identity-federation-for-ci.md) | Workload Identity Federation for GitHub Actions | Accepted |
| [0006](0006-dbt-staging-views-and-mart-tables.md) | dbt: staging views and mart tables in separate datasets | Superseded by 0014 |
| [0007](0007-citibike-monthly-with-two-month-lag.md) | Citi Bike loaded monthly, two months behind | Accepted |
| [0008](0008-one-package-one-lake-layout.md) | One Python package, one lake layout | Accepted |
| [0009](0009-control-totals-and-success-manifests.md) | Control totals and success manifests | Accepted |
| [0010](0010-true-utc-instants-and-new-york-days.md) | True UTC instants and New York calendar days | Accepted |
| [0011](0011-trip-dedupe-in-staging.md) | Trips de-duplicated in staging, not filtered by month | Accepted |
| [0012](0012-two-gcp-projects-built-from-code.md) | Two GCP projects built from code, least-privilege identities | Accepted |
| [0013](0013-atomic-partition-loads-with-audit.md) | Atomic partition loads with a load audit | Accepted |
| [0014](0014-dbt-layers-time-and-grain.md) | dbt in three layers, New York time, one grain per model | Accepted |
| [0015](0015-expected-vs-actual-effects.md) | Weather effects as expected vs actual trips | Accepted |
| [0016](0016-trip-archives-stay-at-the-source.md) | Trip archives stay at the source; Bronze keeps their record | Accepted |
| [0017](0017-airflow-3-from-a-versioned-image.md) | Airflow 3 locally, from a versioned image | Accepted |
