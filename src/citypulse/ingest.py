"""Land one period of one source in the lake: Bronze as received, Silver typed, manifest last.

Two phases, so a failed run never costs us the last good version:

    prepare (local, nothing in the lake changes)
        fetch or download the source, validate it, build Silver, check the control totals
    publish (only if prepare succeeded)
        1. delete the old manifest   (the period is "not ready" while it is rewritten)
        2. write Bronze              (weather, air: the response as received; trips: the
                                      archive's record — URL, ETag, every file's CRC-32)
        3. write Silver              (for trips: old parts removed first)
        4. write the manifest        (only now is the period visible)

The manifest is the success marker: downstream steps only read periods that have one, so a run
that dies during publish is invisible and re-running it is safe. It also carries the control
totals — rows per source file, counted from the source bytes — that the warehouse load is
reconciled against.
"""

from __future__ import annotations

import json
import logging
import time
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from citypulse import lake as paths
from citypulse import openmeteo
from citypulse.citibike import TRIP_SCHEMA, convert, count_rows, trip_members, zip_url
from citypulse.http import Http
from citypulse.lake import Lake

log = logging.getLogger("citypulse")


class ReconciliationError(Exception):
    """What was parsed does not match what the source holds."""


def ingest_day(source: str, day: date, lake: Lake, http: Http, now: datetime) -> dict[str, Any]:
    """Weather or air quality for one New York day that is already over at `now` (UTC)."""
    if now < openmeteo.day_end(day):
        raise ValueError(
            f"{source} {day}: the New York day is not over yet; values would be forecasts"
        )
    today = now.astimezone(UTC).date()

    raw = openmeteo.fetch(source, day, http, today)
    table = openmeteo.to_table(
        source, json.loads(raw), day
    )  # the contract: raises before any write

    manifest_rel = paths.manifest_path(source, day.isoformat())
    bronze, silver = paths.bronze_day(source, day), paths.silver_day(source, day)
    lake.delete(manifest_rel)
    lake.write_bytes(bronze, raw)
    with lake.parquet_writer(silver, table.schema) as writer:
        writer.write_table(table)
    manifest = {
        "source": source,
        "period": day.isoformat(),
        "source_url": openmeteo.endpoint(source, day, today),
        "extracted_at": now.astimezone(UTC).isoformat(timespec="seconds"),
        "rows": table.num_rows,
        "null_counts": openmeteo.null_counts(table),
        "bronze": bronze,
        "silver": [silver],
    }
    lake.write_json(manifest_rel, manifest)
    return manifest


def ingest_month(month: date, lake: Lake, http: Http, workdir: Path) -> dict[str, Any]:
    """Every Citi Bike trip CSV of one month (`month` = its first day)."""
    url = zip_url(month)
    local_zip = workdir / f"{month:%Y%m}-citibike-tripdata.zip"
    local_parts: list[Path] = []
    try:
        started = time.monotonic()
        download = http.download(url, local_zip)
        log.info(
            "trips %s: downloaded %.0f MB in %.0f s",
            f"{month:%Y-%m}",
            download.size / 1e6,
            time.monotonic() - started,
        )
        files, local_parts, members = _convert_all(local_zip, month, workdir)

        manifest_rel = paths.manifest_path("citibike", f"{month:%Y-%m}")
        bronze = paths.bronze_trips(month)
        silver = [paths.silver_trips_part(month, i) for i in range(len(local_parts))]
        record = {
            "url": url,
            "size": download.size,
            "etag": download.etag,
            "last_modified": download.last_modified,
            "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "members": members,
        }
        lake.delete(manifest_rel)
        lake.write_json(bronze, record)
        lake.delete_dir(paths.silver_trips_dir(month))
        started = time.monotonic()
        for rel, local in zip(silver, local_parts, strict=True):
            lake.put_file(rel, local)
        log.info(
            "trips %s: published %d parts in %.0f s",
            f"{month:%Y-%m}",
            len(silver),
            time.monotonic() - started,
        )
    finally:
        local_zip.unlink(missing_ok=True)
        for local in local_parts:
            local.unlink(missing_ok=True)

    manifest = {
        "source": "citibike",
        "period": f"{month:%Y-%m}",
        "source_url": url,
        "extracted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": sum(f["rows"] for f in files),
        "files": files,
        "bronze": bronze,
        "silver": silver,
    }
    lake.write_json(manifest_rel, manifest)
    return manifest


def _convert_all(
    local_zip: Path, month: date, workdir: Path
) -> tuple[list[dict], list[Path], list[dict]]:
    """Convert every trip CSV to a local Parquet part, checking each against its row count.

    Also returns the archive's full listing (name, sizes, CRC-32 of every entry) for Bronze.
    """
    files: list[dict] = []
    parts: list[Path] = []
    try:
        with zipfile.ZipFile(local_zip) as zf:
            members = trip_members(zf)
            trip_names = {info.filename for info in members}
            listing = [
                {
                    "name": info.filename,
                    "size": info.file_size,
                    "compress_size": info.compress_size,
                    "crc32": info.CRC,
                    "trip_csv": info.filename in trip_names,
                }
                for info in zf.infolist()
            ]
            if not members:
                raise ReconciliationError(f"{local_zip.name}: no trip CSV in the archive")
            for index, info in enumerate(members):
                expected = count_rows(zf, info)
                part = workdir / f"{month:%Y%m}-part-{index:03d}.parquet"
                parts.append(part)
                with pq.ParquetWriter(part, TRIP_SCHEMA) as writer:
                    written = convert(zf, info, month, writer)
                if written != expected:
                    raise ReconciliationError(
                        f"{info.filename}: source has {expected} rows, parsed {written}"
                    )
                files.append(
                    {"name": info.filename, "rows": written, "uncompressed_bytes": info.file_size}
                )
                log.info(
                    "trips %s: %s → %d rows (matches the source)",
                    f"{month:%Y-%m}",
                    info.filename,
                    written,
                )
    except BaseException:
        for part in parts:
            part.unlink(missing_ok=True)
        raise
    return files, parts, listing
