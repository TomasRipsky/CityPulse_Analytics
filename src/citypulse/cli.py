"""citypulse — the command line.

    citypulse ingest weather     --from 2025-01-01 [--to 2025-01-31]   source → lake
    citypulse ingest air-quality --from 2025-01-01 [--to 2025-01-31]
    citypulse ingest trips       --from 2025-01    [--to 2025-03]
    citypulse load   <same sources and ranges>     --project P          lake → BigQuery raw

The lake is `--lake`, else $CITYPULSE_LAKE_URI, else the local folder `.lake`.
The BigQuery project is `--project`, else $CITYPULSE_BQ_PROJECT.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from citypulse.http import Http, NotPublishedError
from citypulse.ingest import ReconciliationError, ingest_day, ingest_month
from citypulse.lake import Lake
from citypulse.warehouse import NotReadyError, load_period

log = logging.getLogger("citypulse")
SOURCES = {"weather": "weather", "air-quality": "air_quality", "trips": "citibike"}


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def months(start: date, end: date) -> list[date]:
    out, current = [], start
    while current <= end:
        out.append(current)
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return out


def bigquery_client(project: str):
    from google.cloud import bigquery  # imported here: `ingest` works without the BigQuery client

    return bigquery.Client(project=project)


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {text!r}") from exc


def _month(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM, got {text!r}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="citypulse", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("ingest", "land source data in the lake"),
        ("load", "load lake periods into BigQuery's raw tables"),
    ):
        sub = commands.add_parser(command, help=help_text)
        sources = sub.add_subparsers(dest="source", required=True)
        for name in SOURCES:
            monthly = name == "trips"
            kind, unit = (_month, "YYYY-MM") if monthly else (_day, "YYYY-MM-DD")
            src = sources.add_parser(
                name, help=f"{name}, one {'month' if monthly else 'day'} at a time"
            )
            src.add_argument("--from", dest="start", type=kind, required=True, metavar=unit)
            src.add_argument(
                "--to", dest="end", type=kind, metavar=unit, help="inclusive; default --from"
            )
            src.add_argument("--lake", default=os.environ.get("CITYPULSE_LAKE_URI", ".lake"))
            if command == "load":
                src.add_argument("--project", default=os.environ.get("CITYPULSE_BQ_PROJECT"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request is noise
    parser = _parser()
    args = parser.parse_args(argv)
    end = args.end or args.start
    if end < args.start:
        parser.error("--to is before --from")
    if args.command == "load" and not args.project:
        parser.error("load needs --project or $CITYPULSE_BQ_PROJECT")

    source, monthly = SOURCES[args.source], args.source == "trips"
    periods = months(args.start, end) if monthly else days(args.start, end)
    lake = Lake(args.lake)
    log.info("lake: %s", args.lake)
    try:
        if args.command == "load":
            client = bigquery_client(args.project)
            for period in periods:
                label = f"{period:%Y-%m}" if monthly else period.isoformat()
                audit = load_period(source, label, lake, client, args.project)
                log.info("loaded %s %s: %d rows", source, label, audit["loaded_rows"])
        elif monthly:
            http = Http()
            with tempfile.TemporaryDirectory() as workdir:
                for month in periods:
                    manifest = ingest_month(month, lake, http, Path(workdir))
                    log.info("trips %s: %d rows", f"{month:%Y-%m}", manifest["rows"])
        else:
            http, now = Http(), datetime.now(UTC)
            for day in periods:
                manifest = ingest_day(source, day, lake, http, now)
                log.info("%s %s: %d rows", source, day, manifest["rows"])
    except NotPublishedError as exc:
        print(f"citypulse: not published at the source yet — {exc}", file=sys.stderr)
        return 1
    except NotReadyError as exc:
        print(f"citypulse: not ingested into the lake — {exc}", file=sys.stderr)
        return 1
    except ReconciliationError as exc:
        print(f"citypulse: control totals do not match — {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
