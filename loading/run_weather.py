"""
Runner — carga de clima Silver → BigQuery Staging.

Uso:
    python -m loading.run_weather                      # carga hoy
    python -m loading.run_weather --date 2026-03-06    # fecha específica
    python -m loading.run_weather --dry-run            # muestra qué cargaría sin ejecutar
"""

import argparse
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",    type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    loading_date = date.fromisoformat(args.date) if args.date else date.today()
    project_id   = os.environ["GOOGLE_CLOUD_PROJECT"]
    bucket_name  = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")

    gcs_uri = (
        f"gs://{bucket_name}/silver/weather/"
        f"year={loading_date.year}/month={loading_date.month:02d}/"
        f"day={loading_date.day:02d}/weather_{loading_date.strftime('%Y%m%d')}.parquet"
    )

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Date       : {loading_date}")
        print(f"Source     : {gcs_uri}")
        print(f"Destination: {project_id}.citypulse_staging.weather")
        print(f"Strategy   : append incremental (delete + insert)")
        return

    from loading.loaders.weather_loader import WeatherLoader
    loader = WeatherLoader(project_id=project_id, bucket_name=bucket_name)
    rows = loader.load(loading_date=loading_date)
    print(f"\n✅ Weather loaded to BigQuery: {rows} rows for {loading_date}")


if __name__ == "__main__":
    main()