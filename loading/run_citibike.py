"""
Runner — carga de Citibike Silver → BigQuery Staging.

Uso:
    python -m loading.run_citibike
    python -m loading.run_citibike --year 2025 --month 1
    python -m loading.run_citibike --dry-run
"""

import argparse
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv()


def parse_args():
    today = date.today()
    month_offset  = today.month - 2
    default_year  = today.year if month_offset > 0 else today.year - 1
    default_month = month_offset if month_offset > 0 else 12 + month_offset

    parser = argparse.ArgumentParser()
    parser.add_argument("--year",    type=int, default=default_year)
    parser.add_argument("--month",   type=int, default=default_month)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    project_id  = os.environ["GOOGLE_CLOUD_PROJECT"]
    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")

    gcs_uri = (
        f"gs://{bucket_name}/silver/citibike/"
        f"year={args.year}/month={args.month:02d}/"
        f"citibike_{args.year}{args.month:02d}.parquet"
    )

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Period     : {args.year}-{args.month:02d}")
        print(f"Source     : {gcs_uri}")
        print(f"Destination: {project_id}.citypulse_staging.citibike")
        print(f"Strategy   : truncate + reload mensual (delete month + insert)")
        return

    from loading.loaders.citibike_loader import CitibikeLoader
    loader = CitibikeLoader(project_id=project_id, bucket_name=bucket_name)
    rows = loader.load(year=args.year, month=args.month)
    print(f"\n✅ Citibike loaded to BigQuery: {rows} rows for {args.year}-{args.month:02d}")


if __name__ == "__main__":
    main()