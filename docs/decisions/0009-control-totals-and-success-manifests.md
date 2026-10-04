# 0009 — Control totals and success manifests

- **Status:** Accepted
- **Date:** 2026-10-04

## Context
Data-quality tests look *inside* the data that was loaded: `not_null`, `unique`,
"members + casual riders = total". If part of a source never arrives, what did arrive is still
perfectly consistent and every test passes. Version 1 lost most of its trips exactly this way
(each monthly ZIP holds several CSV files and only one was read). A step that dies halfway is the
other risk: a reader cannot tell a finished folder from a half-written one.

## Decision
Every ingested period ends with a **manifest**, written **last**, at
`_manifests/<source>/<period>.json`. Ingestion first *prepares* everything locally — fetch,
validate, build Silver, check the totals — and only then *publishes*:

1. delete the old manifest — the period is "not ready" while it is rewritten;
2. write Bronze, then Silver;
3. write the manifest.

A run that fails while preparing leaves the last good version untouched.

The manifest is the success marker (readers only trust periods that have one) **and** the
control total: for trips, the rows of each CSV counted on the raw bytes (lines minus header),
independently of the CSV parser. Ingestion fails before the manifest if the parser's rows differ
from that count. The warehouse load records expected and loaded rows per period, and a dbt
test fails on any difference or missing period.

## Alternatives considered
- Trust internal-consistency tests — they cannot see missing rows.
- Count rows from the Parquet that was written — counts our own output; a parser that skips rows
  would agree with itself.
- An empty `_SUCCESS` flag — says "complete" but not "how much".

## Consequences
- A truncated or half-written period is never loaded; a re-run is always safe.
- Trip ingestion reads every CSV twice (count, then convert): ~10 s per month, worth it.
- Manifests are small JSON files any later step can audit.
