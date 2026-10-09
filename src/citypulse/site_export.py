"""Export the small, public aggregates the showcase site is built from (site/src/data/).

The story page reads CSVs; the BI page reads Parquet files in `bi/` with DuckDB in the browser
(typed columns, compressed, queried in place).

The site never queries BigQuery: it is built from these files, committed with the site, so a
build needs no cloud credentials. Only aggregates leave the warehouse (Citi Bike's licence allows
analyses, not republishing the trips). Dates are written as text and there are no timestamps, so a
browser reads every value as it is.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as pq

EXPORTS = {
    "daily.csv": """
        select format_date('%F', local_date) as date, weekday, day_type, holiday, trips,
            member_trips, casual_trips, electric_trips, duration_median_min,
            temperature_mean_c, apparent_temperature_mean_c, precipitation_mm, snowfall_cm,
            wet_hours, wind_gusts_max_kmh, aqi_mean, aqi_category
        from `{project}.marts.fct_city_day` where trips_loaded order by local_date""",
    "hourly_profile.csv": """
        select if(day_type = 'workday', 'workday', 'weekend or holiday') as day_type, local_hour,
            round(avg(if(is_dry, trips, null))) as dry_trips,
            -- rain only (no snow), and only where at least 5 wet hours make an average
            if(countif(precipitation_mm >= 1) >= 5,
               round(avg(if(precipitation_mm >= 1, trips, null))), null) as wet_trips,
            countif(precipitation_mm >= 1) as wet_hours
        from `{project}.marts.fct_city_hour`
        where trips_loaded and not service_closed and coalesce(snowfall_cm, 0) = 0
        group by 1, 2 order by 1, 2""",
    "effects.csv": """
        select condition, band, band_order, is_reference, rider, periods, trips, expected_trips,
            effect_pct
        from `{project}.marts.mart_condition_effects` order by condition, band_order, rider""",
    "temperature_curve.csv": """
        select band_from_c, band_to_c, day_type, days, trips_per_day, casual_share_pct
        from `{project}.marts.mart_temperature_curve` order by day_type, band_from_c""",
    "temperature_response.csv": """
        select rider, days, pct_per_degree, correlation
        from `{project}.marts.mart_temperature_response` order by rider""",
    "months.csv": """
        select format_date('%Y-%m', month) as month, trips, trips_per_day, member_share_pct,
            electric_share_pct, temperature_mean_c, precipitation_mm, wet_days, snow_days, aqi_mean
        from `{project}.marts.mart_city_month` where days_with_trip_data > 0 order by month""",
}

# The BI page's files: one per report model, every column (the models are shaped for the page).
BI_EXPORTS = {
    f"{model}.parquet": f"select * from `{{project}}.marts.{model}` order by {order}"
    for model, order in {
        "rpt_day_riders": "local_date, rider, bike_type",
        "rpt_week_hours": "month, weekday_number, local_hour, rider",
        "rpt_stations": "station_id",
        "rpt_station_months": "station_id, month, day_type, rider",
        "rpt_station_hours": "station_id, day_type, local_hour",
        "rpt_weather_losses": "month, condition, band_order, rider",
        "rpt_load_audit": "source, month",
    }.items()
}


def export(client, project: str, out: Path) -> list[str]:
    """Write every export and summary.json into `out`; return the file names."""
    out.mkdir(parents=True, exist_ok=True)
    tables = {}
    for name, sql in EXPORTS.items():
        tables[name] = client.query(sql.format(project=project)).to_arrow()
        csv.write_csv(tables[name], out / name)
    daily = tables["daily.csv"]
    summary = {
        "days": daily.num_rows,
        "trips": pc.sum(daily["trips"]).as_py(),
        "first_day": pc.min(daily["date"]).as_py(),
        "last_day": pc.max(daily["date"]).as_py(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "bi").mkdir(exist_ok=True)
    # The BI page's calendar: the daily facts again, as Parquet with a real date type. DuckDB in the
    # browser sniffs CSV headers, and some browsers read the quotes into the column names.
    i = daily.schema.get_field_index("date")
    days = daily.set_column(
        i, "date", pc.cast(pc.strptime(daily["date"], "%Y-%m-%d", "s"), pa.date32())
    )
    pq.write_table(days, out / "bi" / "days.parquet", compression="zstd")
    for name, sql in BI_EXPORTS.items():
        table = client.query(sql.format(project=project)).to_arrow()
        pq.write_table(table, out / "bi" / name, compression="zstd")
    return [*EXPORTS, "summary.json", "bi/days.parquet", *(f"bi/{name}" for name in BI_EXPORTS)]
