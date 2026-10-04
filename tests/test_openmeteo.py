import json
from datetime import date, datetime
from pathlib import Path

import pytest

from citypulse import openmeteo
from citypulse.openmeteo import AIR_VARS, WEATHER_VARS, endpoint, null_counts, to_table

FIXTURES = Path(__file__).parent / "fixtures" / "openmeteo"


def payload(source: str, day: str) -> dict:
    return json.loads((FIXTURES / f"{source}_{day}.json").read_text())


@pytest.mark.parametrize("source", ["weather", "air_quality"])
@pytest.mark.parametrize(
    ("day", "hours", "first_utc"),
    [
        ("2025-01-15", 24, "2025-01-15T05:00:00+00:00"),  # EST: local midnight is 05:00Z
        ("2025-03-09", 23, "2025-03-09T05:00:00+00:00"),  # spring forward: 02:00 never happens
        ("2025-11-02", 25, "2025-11-02T04:00:00+00:00"),  # fall back: 01:00 happens twice
    ],
)
def test_a_local_day_has_its_true_hours(source, day, hours, first_utc):
    table = to_table(source, payload(source, day), date.fromisoformat(day))
    assert table.num_rows == hours
    assert table["observed_at"][0].as_py() == datetime.fromisoformat(first_utc)
    assert set(table["local_date"].to_pylist()) == {date.fromisoformat(day)}
    assert str(table.schema.field("observed_at").type) == "timestamp[us, tz=UTC]"


def test_columns_are_the_api_variables():
    weather = to_table("weather", payload("weather", "2025-01-15"), date(2025, 1, 15))
    air = to_table("air_quality", payload("air_quality", "2025-01-15"), date(2025, 1, 15))
    assert weather.column_names == ["observed_at", "local_date", *WEATHER_VARS]
    assert air.column_names == ["observed_at", "local_date", *AIR_VARS]
    assert str(weather.schema.field("weather_code").type) == "int64"
    assert str(air.schema.field("us_aqi").type) == "int64"
    assert str(weather.schema.field("temperature_2m").type) == "double"


def test_a_missing_variable_is_an_error():
    data = payload("weather", "2025-01-15")
    del data["hourly"]["snowfall"]
    with pytest.raises(ValueError, match="snowfall"):
        to_table("weather", data, date(2025, 1, 15))


def test_times_must_be_unix_utc():
    data = payload("weather", "2025-01-15")
    data["utc_offset_seconds"] = -18000
    with pytest.raises(ValueError, match="utc_offset_seconds"):
        to_table("weather", data, date(2025, 1, 15))
    data = payload("weather", "2025-01-15")
    data["hourly"]["time"] = ["2025-01-15T00:00"] * len(data["hourly"]["time"])
    with pytest.raises(ValueError, match="unix"):
        to_table("weather", data, date(2025, 1, 15))


def test_a_gap_in_the_hours_is_an_error():
    data = payload("weather", "2025-01-15")
    for key in data["hourly"]:
        del data["hourly"][key][10]
    with pytest.raises(ValueError, match="hours"):
        to_table("weather", data, date(2025, 1, 15))


def test_null_hours_are_kept_and_counted():
    data = payload("air_quality", "2025-01-15")
    data["hourly"]["us_aqi"][12] = None  # 12:00Z on the 15th = 07:00 local, inside the day
    table = to_table("air_quality", data, date(2025, 1, 15))
    assert table.num_rows == 24
    assert null_counts(table)["us_aqi"] == 1
    assert null_counts(table)["pm2_5"] == 0


def test_endpoint_switches_to_forecast_for_the_last_week():
    today = date(2025, 6, 10)
    assert endpoint("weather", date(2025, 6, 2), today) == openmeteo.ARCHIVE_URL  # day+1 = 06-03
    assert endpoint("weather", date(2025, 6, 3), today) == openmeteo.FORECAST_URL
    assert endpoint("air_quality", date(2025, 6, 9), today) == openmeteo.AIR_URL


def test_fetch_asks_for_two_utc_days_in_unix_time():
    seen = {}

    class FakeHttp:
        def get_json(self, url, params):
            seen.update(url=url, params=params)
            return {}

    openmeteo.fetch("weather", date(2025, 1, 31), FakeHttp(), today=date(2025, 6, 1))
    assert seen["url"] == openmeteo.ARCHIVE_URL
    params = seen["params"]
    assert (params["start_date"], params["end_date"]) == ("2025-01-31", "2025-02-01")
    assert (params["timezone"], params["timeformat"]) == ("GMT", "unixtime")
    assert params["hourly"] == ",".join(WEATHER_VARS)
    assert (params["latitude"], params["longitude"]) == (40.7128, -74.006)
