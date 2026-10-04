"""Record Open-Meteo responses for the tests. Dev tool: hits the real APIs.

Run from the repo root:  uv run python tests/record_fixtures.py
Days: a normal winter day and both 2025 daylight-saving Sundays.
"""

import json
from datetime import date
from pathlib import Path

from citypulse.http import Http
from citypulse.openmeteo import SOURCES, fetch

FIXTURES = Path(__file__).parent / "fixtures" / "openmeteo"
DAYS = (date(2025, 1, 15), date(2025, 3, 9), date(2025, 11, 2))


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    http = Http()
    for source in SOURCES:
        for day in DAYS:
            data = fetch(source, day, http, today=date.today())
            data.pop("generationtime_ms", None)  # changes on every call
            path = FIXTURES / f"{source}_{day}.json"
            path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
            print(path.name, len(data["hourly"]["time"]), "hours")


if __name__ == "__main__":
    main()
