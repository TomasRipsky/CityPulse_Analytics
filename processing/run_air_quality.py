"""
Runner — procesador de calidad del aire Bronze → Silver.

Uso:
    python -m processing.run_air_quality
    python -m processing.run_air_quality --date 2025-01-15
    python -m processing.run_air_quality --dry-run
"""

import argparse
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    processing_date = date.fromisoformat(args.date) if args.date else date.today()
    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")

    from processing.processors.air_quality_processor import AirQualityProcessor
    processor = AirQualityProcessor(bucket_name=bucket_name)
    df = processor.process(processing_date)

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Rows    : {len(df)}")
        print(f"Columns : {list(df.columns)}")
        print(df.head(3).to_string())
        return

    from processing.loaders.gcs_silver_loader import GCSSilverLoader
    loader = GCSSilverLoader(bucket_name=bucket_name)
    uri = loader.load(df=df, source_name=processor.source_name, processing_date=processing_date)
    print(f"\n✅ Air Quality Silver uploaded to: {uri}")


if __name__ == "__main__":
    main()