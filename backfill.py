"""
Backfill script — carga datos históricos de clima y calidad del aire.

Ejecuta el pipeline completo (ingestion → processing → loading) para
cada día de los meses especificados.

Uso:
    python backfill.py
    python backfill.py --dry-run
"""

import argparse
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
load_dotenv()

# Meses a cargar — añade o quita según necesites
MONTHS_TO_BACKFILL = [
    (2025, 1),  # Noviembre 2025
]


def get_days_in_month(year: int, month: int) -> list[date]:
    """Devuelve todos los días de un mes dado."""
    days = []
    d = date(year, month, 1)
    while d.month == month:
        days.append(d)
        d += timedelta(days=1)
    return days


def process_date(target_date: date, bucket_name: str, project_id: str, dry_run: bool):
    """Ejecuta el pipeline completo para una fecha dada."""

    print(f"\n{'='*50}")
    print(f"Processing {target_date}")
    print(f"{'='*50}")

    # ── INGESTION ──────────────────────────────────
    from ingestion.extractors.weather_extractor import WeatherExtractor
    from ingestion.extractors.air_quality_extractor import AirQualityExtractor
    from ingestion.loaders.gcs_loader import GCSLoader

    gcs_loader = GCSLoader(bucket_name=bucket_name)

    print(f"[1/6] Extracting weather...")
    weather_extractor = WeatherExtractor()
    weather_data = weather_extractor.extract(target_date)
    if not dry_run:
        uri = gcs_loader.load(data=weather_data, source_name=weather_extractor.source_name, extraction_date=target_date)
        print(f"      ✅ Bronze: {uri}")
    else:
        print(f"      DRY RUN — skipping upload")

    print(f"[2/6] Extracting air quality...")
    aq_extractor = AirQualityExtractor()
    aq_data = aq_extractor.extract(target_date)
    if not dry_run:
        uri = gcs_loader.load(data=aq_data, source_name=aq_extractor.source_name, extraction_date=target_date)
        print(f"      ✅ Bronze: {uri}")
    else:
        print(f"      DRY RUN — skipping upload")

    # ── PROCESSING ─────────────────────────────────
    from processing.processors.weather_processor import WeatherProcessor
    from processing.processors.air_quality_processor import AirQualityProcessor
    from processing.loaders.gcs_silver_loader import GCSSilverLoader

    silver_loader = GCSSilverLoader(bucket_name=bucket_name)

    print(f"[3/6] Processing weather...")
    weather_processor = WeatherProcessor(bucket_name=bucket_name)
    weather_df = weather_processor.process(target_date)
    if not dry_run:
        uri = silver_loader.load(df=weather_df, source_name=weather_processor.source_name, processing_date=target_date)
        print(f"      ✅ Silver: {uri} ({len(weather_df)} rows)")
    else:
        print(f"      DRY RUN — {len(weather_df)} rows would be uploaded")

    print(f"[4/6] Processing air quality...")
    aq_processor = AirQualityProcessor(bucket_name=bucket_name)
    aq_df = aq_processor.process(target_date)
    if not dry_run:
        uri = silver_loader.load(df=aq_df, source_name=aq_processor.source_name, processing_date=target_date)
        print(f"      ✅ Silver: {uri} ({len(aq_df)} rows)")
    else:
        print(f"      DRY RUN — {len(aq_df)} rows would be uploaded")

    # ── LOADING ────────────────────────────────────
    if dry_run:
        print(f"[5/6] Loading weather to BigQuery... DRY RUN — skipping")
        print(f"[6/6] Loading air quality to BigQuery... DRY RUN — skipping")
        return

    from loading.loaders.weather_loader import WeatherLoader
    from loading.loaders.air_quality_loader import AirQualityLoader

    print(f"[5/6] Loading weather to BigQuery...")
    weather_loader = WeatherLoader(project_id=project_id, bucket_name=bucket_name)
    rows = weather_loader.load(loading_date=target_date)
    print(f"      ✅ BigQuery: {rows} rows")

    print(f"[6/6] Loading air quality to BigQuery...")
    aq_loader = AirQualityLoader(project_id=project_id, bucket_name=bucket_name)
    rows = aq_loader.load(loading_date=target_date)
    print(f"      ✅ BigQuery: {rows} rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")
    project_id  = os.environ["GOOGLE_CLOUD_PROJECT"]

    # Recopilamos todos los días a procesar
    all_days = []
    for year, month in MONTHS_TO_BACKFILL:
        all_days.extend(get_days_in_month(year, month))

    # Excluimos días que ya tenemos cargados para no duplicar
    skip_dates = {
        date(2026, 3, 6),
        date(2026, 3, 7),
        date(2026, 3, 8),
    }
    days_to_process = [d for d in all_days if d not in skip_dates]

    print(f"\n{'='*50}")
    print(f"CityPulse Backfill")
    print(f"{'='*50}")
    print(f"Months  : {[f'{y}-{m:02d}' for y, m in MONTHS_TO_BACKFILL]}")
    print(f"Days    : {len(days_to_process)}")
    print(f"Dry run : {args.dry_run}")
    print(f"{'='*50}\n")

    success = 0
    failed  = []

    for target_date in days_to_process:
        try:
            process_date(
                target_date=target_date,
                bucket_name=bucket_name,
                project_id=project_id,
                dry_run=args.dry_run,
            )
            success += 1
        except Exception as e:
            print(f"\n❌ Failed for {target_date}: {e}")
            failed.append(target_date)
            continue  # seguimos con el siguiente día aunque falle uno

    # Resumen final
    print(f"\n{'='*50}")
    print(f"Backfill complete")
    print(f"Success : {success}/{len(days_to_process)}")
    if failed:
        print(f"Failed  : {[str(d) for d in failed]}")
    print(f"{'='*50}")

    if not args.dry_run and success > 0:
        print(f"\nRun 'dbt run' in transformation/ to update the marts.")


if __name__ == "__main__":
    main()