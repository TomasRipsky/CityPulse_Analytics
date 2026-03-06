"""
Script de prueba — ejecuta el extractor de calidad del aire y sube el resultado a GCS.

Uso:
    python -m ingestion.run_air_quality                   # extrae fecha de hoy
    python -m ingestion.run_air_quality --date 2024-01-15 # extrae fecha específica
    python -m ingestion.run_air_quality --dry-run         # extrae pero no sube a GCS
"""

import argparse
import json
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Air quality extractor runner")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Fecha de extracción en formato YYYY-MM-DD (default: hoy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extrae datos pero no sube a GCS. Útil para validar la API.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from ingestion.extractors.air_quality_extractor import AirQualityExtractor

    extraction_date = (
        date.fromisoformat(args.date) if args.date else date.today()
    )

    extractor = AirQualityExtractor()
    data = extractor.extract(extraction_date)

    if args.dry_run:
        print("\n--- DRY RUN — datos extraídos (no subidos a GCS) ---")
        print(json.dumps(data, indent=2))
        return

    from ingestion.loaders.gcs_loader import GCSLoader

    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")
    loader = GCSLoader(bucket_name=bucket_name)
    uri = loader.load(
        data=data,
        source_name=extractor.source_name,
        extraction_date=extraction_date,
    )
    print(f"\n✅ Datos subidos correctamente a: {uri}")


if __name__ == "__main__":
    main()