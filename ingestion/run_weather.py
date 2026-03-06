"""
Script de prueba — ejecuta el extractor de clima y sube el resultado a GCS.

Uso:
    python run_weather.py                        # extrae fecha de hoy
    python run_weather.py --date 2024-01-15      # extrae fecha específica
    python run_weather.py --dry-run              # extrae pero no sube a GCS

Variables de entorno requeridas:
    GCP_BUCKET_NAME  — nombre del bucket GCS (ej: city-pulse-tr)
"""

import argparse
import json
import os
from datetime import date

from dotenv import load_dotenv

# Carga el archivo .env desde la raíz del proyecto si existe.
# En producción (GitHub Actions, Airflow) estas variables ya estarán
# definidas en el entorno, por lo que load_dotenv no sobreescribe nada.
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Weather extractor runner")
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

    # Importamos aquí para que el dry-run no requiera credenciales GCP
    from ingestion.extractors.weather_extractor import WeatherExtractor

    extraction_date = (
        date.fromisoformat(args.date) if args.date else date.today()
    )

    extractor = WeatherExtractor()
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