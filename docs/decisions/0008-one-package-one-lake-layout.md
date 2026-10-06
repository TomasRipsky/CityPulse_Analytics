# 0008 — One Python package, one lake layout

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** [0002](0002-medallion-lake-in-one-gcs-bucket.md)

## Context
Version 1 split the code into three folders (`ingestion/`, `processing/`, `loading/`), each with
its own `requirements.txt`, a base class and one runner script per source — nine near-identical
CLIs. The lake path convention was rebuilt by hand in six places, so a change to one copy would
silently break the hand-off between steps. Processing a month of trips loaded the whole ZIP and
every row into pandas, which needed 4 GB of swap on a 1 GB machine.

## Decision
- One installable package, `citypulse` (`src/` layout, `uv`, one `pyproject.toml` and lock file),
  with one CLI: `citypulse ingest <source> --from … [--to …]`.
- One module, `citypulse.lake`, owns the layout and the storage. It works on a local folder or a
  `gs://` bucket through `pyarrow.fs`, so the same code runs on a laptop and against GCS:

  ```
  bronze/<source>/date=YYYY-MM-DD/<source>.json          weather, air quality: as received
  bronze/citibike/month=YYYY-MM/YYYYMM-citibike-tripdata.zip
  silver/<source>/date=YYYY-MM-DD/part.parquet           typed, true UTC instants
  silver/citibike/month=YYYY-MM/part-NNN.parquet         one part per CSV in the ZIP
  _manifests/<source>/<period>.json                      written last (see 0009)
  ```
- Silver is written with **pyarrow** only: trip CSVs are streamed in 16 MB blocks, so memory
  stays bounded whatever the size of the month. No pandas.

## Alternatives considered
- Keep the three layers and deduplicate with a shared helper — still nine entry points and three
  dependency sets to keep aligned.
- `google-cloud-storage` for GCS — a second I/O path next to pyarrow's; `pyarrow.fs` already reads
  and writes both local and GCS.
- pandas with chunked reading — works, but pyarrow does the CSV parsing, type conversion and
  Parquet writing natively, with fewer copies.

## Consequences
- One place to change a path; tests run against a temporary local lake.
- One period key per source (`date=` for daily sources, `month=` for trips) instead of
  `year=/month=/day=`: still Hive-style, simpler to build and to read.
- Medallion idea of 0002 unchanged: Bronze keeps the payload as received, Silver is typed Parquet.
