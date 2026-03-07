"""
Runner — procesador de Citibike Bronze → Silver.

Uso:
    python -m processing.run_citibike
    python -m processing.run_citibike --year 2025 --month 1
    python -m processing.run_citibike --dry-run
"""

import argparse
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv()


def parse_args():
    today = date.today()
    month_offset = today.month - 2
    default_year = today.year if month_offset > 0 else today.year - 1
    default_month = month_offset if month_offset > 0 else 12 + month_offset

    parser = argparse.ArgumentParser()
    parser.add_argument("--year",  type=int, default=default_year)
    parser.add_argument("--month", type=int, default=default_month)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")

    from processing.processors.citibike_processor import CitibikeProcessor
    processor = CitibikeProcessor(bucket_name=bucket_name)
    df = processor.process_month(year=args.year, month=args.month)

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Rows    : {len(df)}")
        print(f"Columns : {list(df.columns)}")
        print(df.head(3).to_string())
        return

    from processing.loaders.gcs_silver_loader import GCSSilverLoader
    loader = GCSSilverLoader(bucket_name=bucket_name)
    uri = loader.load_monthly(df=df, source_name=processor.source_name, year=args.year, month=args.month)
    print(f"\n✅ Citibike Silver uploaded to: {uri}")


if __name__ == "__main__":
    main()