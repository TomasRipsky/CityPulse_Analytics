"""citypulse — the command line.

    citypulse ingest weather     --from 2025-01-01 [--to 2025-01-31]
    citypulse ingest air-quality --from 2025-01-01 [--to 2025-01-31]
    citypulse ingest trips       --from 2025-01    [--to 2025-03]

The lake is `--lake`, else $CITYPULSE_LAKE_URI, else the local folder `.lake`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from citypulse.http import Http, NotPublishedError
from citypulse.ingest import ReconciliationError, ingest_day, ingest_month
from citypulse.lake import Lake

log = logging.getLogger("citypulse")
DAY_SOURCES = {"weather": "weather", "air-quality": "air_quality"}


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def months(start: date, end: date) -> list[date]:
    out, current = [], start
    while current <= end:
        out.append(current)
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return out


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
    ingest = commands.add_parser("ingest", help="land source data in the lake")
    sources = ingest.add_subparsers(dest="source", required=True)
    for name in (*DAY_SOURCES, "trips"):
        kind = _month if name == "trips" else _day
        unit = "YYYY-MM" if name == "trips" else "YYYY-MM-DD"
        sub = sources.add_parser(
            name, help=f"{name}, one {'month' if name == 'trips' else 'day'} at a time"
        )
        sub.add_argument("--from", dest="start", type=kind, required=True, metavar=unit)
        sub.add_argument(
            "--to", dest="end", type=kind, metavar=unit, help="inclusive; default --from"
        )
        sub.add_argument("--lake", default=os.environ.get("CITYPULSE_LAKE_URI", ".lake"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = _parser()
    args = parser.parse_args(argv)
    end = args.end or args.start
    if end < args.start:
        parser.error("--to is before --from")

    lake, http = Lake(args.lake), Http()
    try:
        if args.source == "trips":
            with tempfile.TemporaryDirectory() as workdir:
                for month in months(args.start, end):
                    manifest = ingest_month(month, lake, http, Path(workdir))
                    log.info("trips %s: %d rows", f"{month:%Y-%m}", manifest["rows"])
        else:
            source, today = DAY_SOURCES[args.source], date.today()
            for day in days(args.start, end):
                manifest = ingest_day(source, day, lake, http, today)
                log.info("%s %s: %d rows", source, day, manifest["rows"])
    except NotPublishedError as exc:
        print(f"citypulse: not published at the source yet — {exc}", file=sys.stderr)
        return 1
    except ReconciliationError as exc:
        print(f"citypulse: control totals do not match — {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
