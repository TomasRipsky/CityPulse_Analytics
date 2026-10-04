"""Open-Meteo weather and air quality for New York: one New York calendar day at a time.

Times are asked for in UTC as unix seconds (`timezone=GMT`, `timeformat=unixtime`), so every
value is an unambiguous instant. A New York day spans two UTC dates (it starts at 04:00 or 05:00
UTC), so we request both and keep the hours whose New York date is the requested day: 24 hours
normally, 23 on the spring-forward Sunday and 25 on the fall-back Sunday. (Asking the API for
`timezone=America/New_York` instead returns 24 hours at one fixed offset, even on those days.)
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import pyarrow as pa

NY = ZoneInfo("America/New_York")
LATITUDE, LONGITUDE = 40.7128, -74.006  # City Hall, Manhattan

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ARCHIVE_DELAY = timedelta(days=7)  # the reanalysis archive runs ~5 days behind; keep a margin

SOURCES = ("weather", "air_quality")
WEATHER_VARS = (
    "temperature_2m",  # °C at 2 m
    "apparent_temperature",  # °C, "feels like"
    "precipitation",  # mm in the hour (rain + showers + snow water)
    "rain",  # mm
    "snowfall",  # cm
    "wind_speed_10m",  # km/h
    "wind_gusts_10m",  # km/h
    "relative_humidity_2m",  # %
    "cloud_cover",  # %
    "weather_code",  # WMO code
)
AIR_VARS = (
    "pm2_5",  # µg/m³
    "pm10",  # µg/m³
    "ozone",  # µg/m³
    "nitrogen_dioxide",  # µg/m³
    "us_aqi",  # US EPA Air Quality Index
)
INTEGER_VARS = frozenset({"weather_code", "us_aqi"})


class BytesGetter(Protocol):
    def get_bytes(self, url: str, params: dict[str, Any]) -> bytes: ...


def variables(source: str) -> tuple[str, ...]:
    if source == "weather":
        return WEATHER_VARS
    if source == "air_quality":
        return AIR_VARS
    raise ValueError(f"unknown Open-Meteo source {source!r}")


def endpoint(source: str, day: date, today: date) -> str:
    if source == "air_quality":
        return AIR_URL
    variables(source)
    return ARCHIVE_URL if day + timedelta(days=1) <= today - ARCHIVE_DELAY else FORECAST_URL


def fetch(source: str, day: date, http: BytesGetter, today: date) -> bytes:
    """The raw response body covering the New York day `day` (two UTC dates, hourly)."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": "GMT",
        "timeformat": "unixtime",
        "start_date": day.isoformat(),
        "end_date": (day + timedelta(days=1)).isoformat(),
        "hourly": ",".join(variables(source)),
    }
    return http.get_bytes(endpoint(source, day, today), params)


def to_table(source: str, payload: dict[str, Any], day: date) -> pa.Table:
    """The hours of New York day `day`: observed_at (UTC), local_date, one column per variable."""
    names = variables(source)
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError(f"{source} {day}: expected utc_offset_seconds 0 (GMT request)")
    hourly = payload.get("hourly", {})
    missing = [name for name in ("time", *names) if name not in hourly]
    if missing:
        raise ValueError(f"{source} {day}: response lacks {', '.join(missing)}")
    times = hourly["time"]
    if not all(isinstance(t, int) for t in times):
        raise ValueError(f"{source} {day}: times must be unix seconds (timeformat=unixtime)")

    keep = [i for i, t in enumerate(times) if datetime.fromtimestamp(t, NY).date() == day]
    expected = int((_ny_midnight(day + timedelta(days=1)) - _ny_midnight(day)).total_seconds())
    kept = [times[i] for i in keep]
    steps = {b - a for a, b in zip(kept, kept[1:], strict=False)}
    if len(kept) * 3600 != expected or steps - {3600}:
        raise ValueError(f"{source} {day}: got {len(kept)} hours, the day has {expected // 3600}")

    columns: dict[str, pa.Array] = {
        "observed_at": pa.array(kept, pa.int64())
        .cast(pa.timestamp("s", tz="UTC"))
        .cast(pa.timestamp("us", tz="UTC")),
        "local_date": pa.array([day] * len(keep), pa.date32()),
    }
    for name in names:
        kind = pa.int64() if name in INTEGER_VARS else pa.float64()
        columns[name] = pa.array([hourly[name][i] for i in keep], kind)
    return pa.table(columns)


def null_counts(table: pa.Table) -> dict[str, int]:
    return {name: table[name].null_count for name in table.column_names}


def day_end(day: date) -> datetime:
    """The instant (UTC) when New York day `day` is over: the next local midnight."""
    return _ny_midnight(day + timedelta(days=1))


def _ny_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=NY).astimezone(UTC)
