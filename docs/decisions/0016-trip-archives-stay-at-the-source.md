# 0016 — Trip archives stay at the source; Bronze keeps their record

- **Status:** Accepted
- **Date:** 2026-10-05
- **Refines:** [0008](0008-one-package-one-lake-layout.md)

## Context
Bronze keeps what a source returned, so any later step can be replayed. For Citi Bike that meant
copying each monthly ZIP — 400 to 700 MB — into the bucket. Measured on a home connection
(~0.9 MB/s upstream), uploading July 2025 took 18 minutes, almost all of it the ZIP; twenty
months would have taken more than five hours. The copies were deleted after 30 days anyway, and
the archive itself is a public, versioned file that Citi Bike does not rewrite.

## Decision
For trips, Bronze is a **source record** instead of a copy: `bronze/citibike/month=YYYY-MM/source.json`
holds the archive's URL, size, `ETag` and `Last-Modified` as served, the time it was downloaded,
and every entry of the archive — name, size, compressed size and **CRC-32** — in the archive's own
order. Weather and air quality keep their full responses (a few kilobytes each).

## Alternatives considered
- Keep uploading the ZIPs — hours of upload for copies that expired after 30 days.
- Run ingestion in the cloud next to the bucket — fast, but a second runtime to build and pay for.
- Keep nothing — then nobody could say later which version of a file was read.

## Consequences
- A month lands in about a minute plus its download; Silver (~170 MB a month) is what is uploaded.
- To replay a month, download it again; the record proves it is the same file (size, ETag, every
  CSV's CRC-32), or shows exactly what changed.
- If Citi Bike ever removed an archive, Silver would be the only copy left — acceptable for public
  data, and Silver holds every row.
