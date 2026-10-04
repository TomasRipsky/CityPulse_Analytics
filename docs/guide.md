# How CityPulse works

This guide explains the system from the inside: what each part does, why it is built that way,
what it costs, and what went wrong on the way. It is written for someone who knows Python and SQL
but has not seen this project. The README says *what* and *how to run*; this file says *how* and
*why*. Decisions are argued in full in [`decisions/`](decisions/).

**Contents**

1. [The big picture](#1-the-big-picture)
2. [The lake](#2-the-lake)
3. [Ingestion: weather and air quality](#3-ingestion-weather-and-air-quality)
4. [Ingestion: Citi Bike trips](#4-ingestion-citi-bike-trips)
5. [Control totals and the success manifest](#5-control-totals-and-the-success-manifest)
6. [Talking to the internet: retries and downloads](#6-talking-to-the-internet-retries-and-downloads)
7. [How the code is tested](#7-how-the-code-is-tested)
8. [The cloud: projects, Terraform and identities](#8-the-cloud-projects-terraform-and-identities)
9. [Loading the warehouse](#9-loading-the-warehouse)

---

## 1. The big picture

CityPulse asks one question: **does the weather change how New York rides bikes?** Answering it
needs three things measured for the same place and the same hours:

| Source | What it gives us | Grain | How often |
|---|---|---|---|
| Open-Meteo weather | temperature, "feels like", rain, snow, wind, gusts, humidity, clouds, weather code | one row per hour | daily |
| Open-Meteo air quality | PM2.5, PM10, ozone, NO₂, US AQI | one row per hour | daily |
| Citi Bike System Data | every trip: start/end time and station, bike type, member or casual rider | one row per trip | monthly, ~6 weeks late |

The data moves through layers, each with one job:

```mermaid
flowchart LR
  src["Sources<br/>Open-Meteo · Citi Bike"] -->|extract| bronze[("Bronze<br/>as received")]
  bronze -->|type, convert to UTC| silver[("Silver<br/>Parquet")]
  silver -->|manifest written last| ready{{"period ready"}}
  ready -->|load| wh[("BigQuery<br/>raw tables")]
  wh -->|dbt| marts[("marts<br/>answers")]
```

This is the **medallion** pattern. Bronze keeps the source's answer untouched, so any later step
can be replayed without asking the source again. Silver is the same data typed, with correct
instants, in a columnar format that warehouses load cheaply. The warehouse and dbt (next
chapters) turn it into answers.

Everything is driven by one command line, `citypulse`, from one Python package in `src/citypulse/`:

| Module | Job |
|---|---|
| `lake.py` | where files live (local folder or GCS bucket) and the one place the path layout is written |
| `http.py` | HTTP with retries, and downloads that are verified before they are kept |
| `openmeteo.py` | ask Open-Meteo for one New York day and turn the answer into a typed table |
| `citibike.py` | find every trip CSV in a monthly ZIP, count its rows, stream it to Parquet in UTC |
| `ingest.py` | land one period: Bronze → Silver → manifest, in that order |
| `cli.py` | `citypulse ingest …` |

Try it on your laptop — no cloud account needed:

```bash
make setup
uv run citypulse ingest weather --from 2025-03-09          # 23 hours: clocks went forward
uv run citypulse ingest trips --from 2025-01               # 2,124,475 trips, ~1 minute
```

---

## 2. The lake

A *data lake* here is just a folder of files with a fixed layout. `Lake` (in `lake.py`) wraps one
root — a local path such as `.lake`, or `gs://bucket` — behind a handful of methods
(`write_bytes`, `parquet_writer`, `read_table`, `list`, `delete_dir`…). Underneath it is
`pyarrow.fs`, Apache Arrow's filesystem layer, which speaks both local disk and Google Cloud
Storage. That is why the same code runs in tests (a temporary folder), on a laptop (`.lake/`) and
in production (a bucket) — only the root changes, through `CITYPULSE_LAKE_URI`.

```
bronze/weather/date=2025-01-15/weather.json
bronze/air_quality/date=2025-01-15/air_quality.json
bronze/citibike/month=2025-01/202501-citibike-tripdata.zip
silver/weather/date=2025-01-15/part.parquet
silver/citibike/month=2025-01/part-000.parquet … part-002.parquet
_manifests/weather/2025-01-15.json
_manifests/citibike/2025-01.json
```

**Why `key=value` folders?** It is the *Hive partitioning* convention: tools such as BigQuery,
Spark and DuckDB read `date=2025-01-15` as a column, and can skip whole folders when a query
filters on it. One key per source is enough: the daily sources are keyed by the New York day
they describe, trips by the month of the file they came from.

**Why are the path functions in one module?** Every step must agree on where the previous step
wrote. Version 1 rebuilt the same path string in six modules; the smallest change to one copy
would have broken the hand-off silently. Now `bronze_day()`, `silver_trips_part()`,
`manifest_path()` and friends are the only place a path is spelled out, and a test pins the
exact layout.

**Object stores are not file systems.** On GCS a "folder" is only a name prefix, so there is no
atomic "rename the folder when it is complete". That is the reason for the manifest
(chapter 5). `Lake` also only creates directories on local disk: on GCS, `create_dir` could
create a *bucket*, which is never what we want.

---

## 3. Ingestion: weather and air quality

### What we ask for

`openmeteo.fetch()` sends one request per source and day to the
[Open-Meteo](https://open-meteo.com/) APIs: the historical **archive** for days more than a week
old, the **forecast** API (which also serves recent past days) for the last week, and the **air
quality** API. Coordinates are City Hall, Manhattan. No API key is needed; the data is CC BY 4.0.

```
timezone=GMT  timeformat=unixtime  start_date=D  end_date=D+1  hourly=temperature_2m,…
```

### Time, the subtle part

A timestamp only means something with its timezone. `2025-01-15 17:00` in New York is
`2025-01-15 22:00` UTC in winter and would be `21:00` UTC in summer. The rule we follow
([decision 0010](decisions/0010-true-utc-instants-and-new-york-days.md)):

- **store instants in UTC**, as `timestamp[us, tz=UTC]` — unambiguous, comparable across sources;
- **keep the local calendar day as its own column** (`local_date`), because "a day" for a cyclist
  is a New York day, midnight to midnight.

Asking Open-Meteo for `timeformat=unixtime` returns epoch seconds — a count of seconds since
1970 in UTC — so there is nothing to interpret. The catch is *which hours make up a New York day*.
A New York day starts at 05:00 UTC in winter and 04:00 UTC in summer, so it spans two UTC dates.
We request both (48 hours) and keep the hours whose New York date is the day we want:

| Day | Why it is special | Hours kept | First hour (UTC) |
|---|---|---|---|
| 15 Jan 2025 | normal winter day | 24 | 05:00 |
| 9 Mar 2025 | clocks jump 02:00 → 03:00 | **23** | 05:00 |
| 2 Nov 2025 | clocks fall back, 01:00 happens twice | **25** | 04:00 |

> **Problem we hit.** The obvious request — `timezone=America/New_York` — returns 24 hours on
> every day, at one fixed UTC offset (the response has a single `utc_offset_seconds`). On the two
> daylight-saving days that window is shifted by an hour, so one real hour is missing and another
> belongs to the neighbouring day. Verified against the live API on 2026-10-04, which is why the
> request is made in UTC and the day is cut on our side with Python's `zoneinfo`.

**Only finished days.** A New York day is ingested only once it is over (after the next local
midnight). Before that, the API would answer with forecasts, and they would be stored as if they
had been observed.

**Hours are stamped at their end for some variables.** Temperature, humidity, cloud cover and
wind speed are readings *at* the stamped instant. `precipitation`, `rain` and `snowfall` are the
total of the **preceding** hour, and `wind_gusts_10m` its maximum: the value stamped 08:00 is what
fell between 07:00 and 08:00. Bronze and Silver keep Open-Meteo's stamps untouched; the dbt models
shift those four variables back one hour before summing them into days or joining them with the
trips of that hour.

### Turning the answer into a table

`openmeteo.to_table()` is also a small **contract**: it refuses an answer that is not what we
asked for, instead of loading something subtly wrong.

- `utc_offset_seconds` must be 0 and every time must be an integer (unix seconds);
- every requested variable must be present — a renamed variable fails with its name;
- the kept hours must be exactly the length of that New York day, one hour apart.

Columns are `observed_at`, `local_date`, then one column per variable under the API's own name
(`temperature_2m`, `us_aqi`…), doubles except the two codes (`weather_code`, `us_aqi`), which are
integers. A missing value (`null`) is **kept**: the archive sometimes lacks an hour for one
variable, and dropping the row would lose the others. Instead the number of nulls per column goes
into the manifest, where the warehouse tests can see it.

---

## 4. Ingestion: Citi Bike trips

### The source

Citi Bike publishes one ZIP per month on a public S3 bucket
(`https://s3.amazonaws.com/tripdata/YYYYMM-citibike-tripdata.zip`), about six weeks after the
month ends. Inside are **several CSV files, one per million trips** — between two and four in the
months checked, more in a busy summer month:

| Month | Files | Trips |
|---|---|---|
| Jan 2025 | `_1`, `_2`, `_3` | 2,124,475 |
| Nov 2025 | `_1` … `_4` | ~3.4 M |

> **Problem we hit.** Version 1 opened the first `.csv` it found in the archive and stopped. The
> order inside a ZIP is whatever the publisher's tool wrote — November 2025 lists `_4` first —
> so it loaded between 12% and 82% of each month, and every test still passed. `trip_members()`
> now returns **every** CSV, in name order, skipping things that are not trip files (macOS
> `__MACOSX/` metadata, readmes, folders).

The columns, identical from January 2025 to August 2026 (checked on the oldest and newest files):
`ride_id, rideable_type, started_at, ended_at, start_station_name, start_station_id,
end_station_name, end_station_id, start_lat, start_lng, end_lat, end_lng, member_casual`.

### Streaming instead of loading

A month is 400–700 MB zipped and 2–5 million rows. Loading it whole into memory is what forced
version 1 to add 4 GB of swap to its server. `citibike.convert()` instead uses
`pyarrow.csv.open_csv`, a *streaming* reader: it decompresses and parses 16 MB of CSV at a time
(~80,000 trips), converts that batch and hands it to a Parquet writer, then moves on. Memory depends
on the block size and on one CSV (at most a million trips), not on the month: converting one
1-million-row file peaks at about 0.4 GB and takes 1.5 seconds. Read-ahead threads are off: they
saved no time here and cost ~100 MB. A whole January 2025 run takes about a minute (mostly the
download), and the 395 MB ZIP becomes 97 MB of Parquet.

Types are declared, never guessed: station ids are **strings** (most look like `6182.02`, but
Jersey City stations are `JC024`, and a number would lose the trailing zero of `5746.10`), blank
fields become `null`, coordinates are doubles.

### Local time to UTC

Trip times are New York wall-clock readings with milliseconds and no offset
(`2025-01-15 14:52:26.542`). `pyarrow.compute.assume_timezone` attaches `America/New_York` and
the column is stored in UTC. Two readings a year have no single answer:

- **Fall back** (`2025-11-02 01:30`, which happens twice): we take the first occurrence, daylight
  time → `05:30 UTC` (`ambiguous="earliest"`). Trip data cannot tell the two apart — except when
  the end time would then come before the start: a trip read as 01:55 → 01:10 started in daylight
  time and ended in standard time, so its end takes the second occurrence (`06:10 UTC`).
- **Spring forward** (`2025-03-09 02:30`, which never happens): we use the end of the gap,
  `03:00` daylight time → `07:00 UTC` (`nonexistent="latest"`).

A quick check of the result: the busiest hour of January 2025 is **22:00 UTC** — 17:00 in New
York, the evening rush. Version 1, which labelled local times as UTC, showed it as "17:00 UTC".

Two columns record provenance: `source_month` (the file's month) and `source_file` (the CSV it
came from). They make the warehouse table a faithful copy of the files, which is what lets it be
reconciled with the source.

---

## 5. Control totals and the success manifest

Two things can make a lake lie: a source that only partly arrives, and a step that dies halfway.
Both are handled by one small file per period, the **manifest**
([decision 0009](decisions/0009-control-totals-and-success-manifests.md)).

### Order of operations

`ingest.ingest_day()` and `ingest.ingest_month()` work in two phases.

**Prepare — on the local machine; nothing in the lake changes.** Fetch the response or download
the ZIP, check it against the contract, build Silver, check the control totals. If anything is
wrong — the month is not published, the API changed, a count does not match — the run stops here
and the last good version in the lake is untouched.

**Publish — only after prepare succeeded:**

1. **delete** the old manifest — from now on the period is "not ready";
2. write **Bronze** (the response body or the ZIP, exactly as received);
3. write **Silver** (for trips: remove the month's old parts first, then one part per CSV);
4. write the **manifest**, last.

> **Problem we hit.** The first version of this code deleted the manifest and overwrote Bronze
> *before* checking the new data. A re-run that failed — Citi Bike briefly answering 403, a
> download that did not reconcile — would have destroyed a good month that could not be rebuilt
> without the source. A code review caught it; the two-phase order and three tests now prevent it.

Downstream steps only read periods that have a manifest. Writing one object is atomic on GCS
(a reader sees the whole file or nothing), so the manifest turns "many files" into one
all-or-nothing signal:

| The run dies… | What a reader sees |
|---|---|
| before step 1 | the previous complete version |
| between 1 and 4 | no manifest: the period is ignored, and the next run rewrites it |
| after 4 | the new complete version |

This is the *success marker* pattern (Hadoop's `_SUCCESS` file, the ancestor of the transaction
logs in Delta Lake and Iceberg). Step 3's clean-up matters for re-runs: a month re-ingested with
fewer CSVs than before must not keep a stale `part-003.parquet` around.

### Counting from the source

A marker that says "complete" is not enough — version 1's partial months were "complete" too.
The manifest also carries **control totals**: for trips, the rows of each CSV, counted by
`citibike.count_rows()` on the **raw bytes** (number of lines minus the header) — independently of
the CSV parser. If the parser produced a different number, ingestion stops with a
`ReconciliationError` before the manifest is written.

```json
{
  "source": "citibike", "period": "2025-01", "rows": 2124475,
  "files": [
    {"name": "202501-citibike-tripdata_1.csv", "rows": 1000000, "uncompressed_bytes": 195009639},
    {"name": "202501-citibike-tripdata_2.csv", "rows": 1000000, "uncompressed_bytes": 194993655},
    {"name": "202501-citibike-tripdata_3.csv", "rows": 124475,  "uncompressed_bytes": 24209588}
  ],
  "bronze": "bronze/citibike/month=2025-01/202501-citibike-tripdata.zip",
  "silver": ["silver/citibike/month=2025-01/part-000.parquet", "…part-001…", "…part-002…"]
}
```

Why not just count the Parquet rows? Because that counts our own output: a parser that skipped
rows would agree with itself. The control total has to come from the source side. The next step,
the warehouse load, carries the same total forward: it records the expected rows from the
manifest next to the rows it actually loaded, so a test can fail if they ever differ.

The count is physical lines. A quoted value containing a newline would make the two numbers
differ — and so would a parser that silently skipped a line — so the month stops with a
`ReconciliationError` instead of loading something doubtful. Commas inside quoted station names
are fine.

Counting means reading each CSV twice (once to count, once to convert), about ten extra seconds
per month — a cheap price for knowing the numbers are whole.

---

## 6. Talking to the internet: retries and downloads

Networks fail in two different ways, and `http.Http` treats them differently:

- **Temporary failures** — a dropped connection, `429 Too Many Requests`, `5xx` server errors —
  are retried with *exponential backoff*: wait 2 s, 4 s, 8 s… (plus a random fraction so many
  clients do not retry in lockstep), up to 60 s, five attempts. If the server says how long to wait
  (`Retry-After`), we wait that long instead.
- **Permanent failures** — `400`, `404` — are not retried: asking again cannot fix a wrong request.

Downloads of 400–700 MB need one more guarantee. `Http.download()` streams the body to
`<name>.part`, compares the bytes received with the `Content-Length` the server announced, and
only then renames the file into place. A connection that closes early produces a short file, not
an error, so without that check a truncated ZIP could be ingested. On the final failure the
`.part` file is removed: nothing half-downloaded is ever left behind.

S3 answers a missing public file with `403 Forbidden`, not `404`. Both become
`NotPublishedError` — "Citi Bike has not published this month yet" — which the CLI reports in
plain words with exit code 1.

---

## 7. How the code is tested

`make test` runs the suite (`pytest`) in under a second, with no network and no cloud:

- **Recorded fixtures.** `tests/record_fixtures.py` asks the real Open-Meteo APIs once for three
  days (a normal winter day and both daylight-saving Sundays) and saves the answers in
  `tests/fixtures/openmeteo/`. Tests replay them through `httpx.MockTransport`, a fake network
  that serves files. When the API changes, re-recording shows it.
- **Synthetic ZIPs.** Citi Bike tests build tiny ZIPs in memory with exactly the awkward cases:
  members out of order, macOS junk, blank stations, a `JC024` id, the repeated and the missing
  hour.
- **Temporary lakes.** Every test that writes uses pytest's `tmp_path`.
- **Each guard is shown to bite.** For the safety checks — validating before publishing,
  refusing unfinished days, deleting the old manifest first, the reconciliation, removing stale
  parts, cleaning up `.part` files — the guard was removed once and the matching test was watched
  turning red. A test that cannot fail proves nothing.

Lint and formatting are `ruff` (`make lint`); `pre-commit` runs them, plus a secret scanner
(gitleaks) and a guard against committing to `main` or `dev`, before every commit. CI runs lint
and tests on every pull request.

**Live check.** Fixtures can drift from reality, so the real sources were also ingested once into
a local lake on 2026-10-04: 9 March 2025 weather (23 hours), 2 November 2025 air quality
(25 hours) and January 2025 trips — 2,124,475 rows from three CSVs, equal to the raw line count,
every `ride_id` unique.

---

## 8. The cloud: projects, Terraform and identities

Everything in Google Cloud is created from this repository
([decision 0012](decisions/0012-two-gcp-projects-built-from-code.md)). Nothing is clicked in the
console, so the whole environment can be destroyed and rebuilt.

### Two projects

| Project | Holds | Used by |
|---|---|---|
| `citypulse-tr-dev` | a sample: January and July 2025, both daylight-saving weekends | CI, which builds every pull request's dbt models here |
| `citypulse-tr-prod` | the full dataset, January 2025 – August 2026 | the backfill, the site export, the dashboard |

A GCP *project* is the unit of billing and permissions. Separate projects mean code under review
can never read or overwrite the real data, and a mistake in dev cannot cost money in prod.

### Bootstrap, then Terraform

Two steps, because Terraform needs a project (with billing) to put resources in:

```bash
make bootstrap ENV=dev BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX ORG_ID=000000000000
make apply ENV=dev
```

`make bootstrap` runs four `gcloud` commands once per environment: create the project inside
the organisation, link the billing account, enable the budget API, and create a **budget of €5**
that e-mails at 50%, 90% and 100%. A budget only *warns*; it never stops spending.

`make apply` runs Terraform on `infra/gcp/`. Terraform compares the files with what exists and
makes the difference. What it manages:

| File | What |
|---|---|
| `main.tf` | APIs; the lake bucket; datasets `raw`, `staging`, `intermediate`, `marts`; the raw tables; a query quota |
| `iam.tf` | the pipeline service account and its roles; impersonation for the operator; federation for CI (dev) |
| `schemas/*.json` | the raw tables' columns: name, type, description |
| `versions.tf` | Terraform and provider versions (`google` 8.x), and the credentials used |

Details that matter:

- **Bucket** `<project>-lake` in `us-central1`, a free-tier region. Uniform access (permissions
  only through IAM), public access blocked, soft delete off (it would keep — and bill — every
  overwritten object for a week). A lifecycle rule deletes trip ZIPs after 30 days: Silver is the
  copy we keep, and a ZIP can always be downloaded again.
- **`force_destroy` and `delete_contents_on_destroy`:** everything in the lake and the warehouse
  can be rebuilt from the public sources, so `make destroy` is allowed to delete it with its data.
  A teardown that stops on a non-empty bucket is a teardown nobody runs.
- **Query quota:** at most 100 GiB scanned per day per project. BigQuery bills by bytes scanned
  (the first TiB each month is free); the quota is the hard stop the budget is not.
- **State.** Terraform remembers what it created in a *state* file. Here it stays on the
  operator's machine, one *workspace* per environment (`terraform.tfstate.d/dev/`), git-ignored.
  Shared remote state is only worth it when several people or machines apply.

### Who can do what

| Identity | Can | Cannot |
|---|---|---|
| `citypulse-pipeline` (service account) | read/write the lake bucket; read/write tables in the 4 datasets; run BigQuery jobs | anything about IAM, other buckets, other projects |
| the operator (you) | impersonate the pipeline account | — (as owner of the project you can do more, but the pipeline does not run with it) |
| GitHub Actions, dev only | become the pipeline account, from this repo's `citypulse-*` workflows | anything in prod; `pull_request_target` runs |

*Impersonation* means a person asks Google for a short-lived token **of the service account**.
Set it up once per machine; every Google client library on it (Python, Terraform, Airflow) then
acts as the pipeline:

```bash
gcloud auth application-default login \
  --impersonate-service-account=citypulse-pipeline@citypulse-tr-dev.iam.gserviceaccount.com
```

Running locally with that token is the honest test of least privilege: if the account lacks a
permission, your laptop run fails the same way CI would. The organisation forbids service-account
keys, so there is no key file anywhere.

GitHub Actions gets in through **Workload Identity Federation**: each workflow run receives a
signed OIDC token from GitHub saying which repository, workflow and event it is; Google checks
that token against the pool's *attribute condition* and swaps it for a short-lived token of the
pipeline account. The condition here admits only this repository (by its immutable numeric id —
a renamed or re-created repository gets a new one), only workflow files named `citypulse-*`,
and never `pull_request_target` (an event that runs with the base repository's identity on code
from a fork).

> **Problem we hit.** The first `make apply` failed with `403 Permission
> 'iam.workloadIdentityPools.create' denied` — for the project owner. The IAM API had been
> enabled seconds earlier by the same apply, and Google takes a minute or two to propagate it.
> Re-running worked. Terraform now waits 90 seconds (`time_sleep`) after enabling the APIs before
> creating the pool, so a fresh `destroy` → `apply` works in one go.

---

## 9. Loading the warehouse

`citypulse load <source> --from … [--to …]` (or `make load ENV=…`) moves Silver into BigQuery's
`raw` dataset, one period at a time ([decision 0013](decisions/0013-atomic-partition-loads-with-audit.md)).

### One period, one partition, one job

Each raw table is **partitioned**: BigQuery stores it as separate slices by the value of one
column. `weather_hourly` and `air_quality_hourly` have one partition per New York day
(`local_date`); `trips` has one per source file month (`source_month`). Queries that filter on
that column only read the slices they need — cheaper and faster.

The loader writes to the **partition decorator**, the table name plus `$` and the partition:

```
citypulse-tr-prod.raw.trips$202501        ← January 2025's trips, nothing else
citypulse-tr-prod.raw.weather_hourly$20250309
```

with `WRITE_TRUNCATE`. BigQuery replaces exactly that partition with the files of the period, in
one job. Either the job succeeds and the partition holds the new data, or it fails and the old data
is still there: there is no moment with half a day, and running it twice gives the same table.
(Every row must belong to the partition being written; it does by construction, because Silver is
written per period.)

### Only what is ready, and counted

The loader reads the period's **manifest** first. No manifest means the period was never ingested,
or its ingestion failed: `NotReadyError`, nothing loaded. The load uses exactly the Silver files the
manifest lists, never a wildcard, so a stray file cannot slip in. The schema comes from the
table — which Terraform created from `infra/gcp/schemas/` — and is never guessed from the files.
A test (`tests/test_schemas.py`) compares those JSON schemas with what the Python code writes, so
the two cannot drift apart unnoticed.

After the job, a row goes into `raw.load_audit`:

| source | period | partition_id | expected_rows | loaded_rows | files | manifest_extracted_at | loaded_at |
|---|---|---|---|---|---|---|---|
| citibike | 2025-01 | 202501 | 2124475 | 2124475 | 3 | … | … |

`expected_rows` is the manifest's count, which came from the source bytes; `loaded_rows` is what
BigQuery says it wrote. If they differ, the row is still recorded and the command fails. The
chain is complete: source file → manifest → load job → audit row, each step counting the same
rows.

> **Problem we hit.** The audit column was first called `partition`. It loads fine, but
> `partition` is a reserved word in BigQuery SQL, so every query needs backticks around it — the
> first verification query failed with `Syntax error: … keyword PARTITION`. Renamed to
> `partition_id` before anything depended on it.
