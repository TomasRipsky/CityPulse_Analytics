"""
Script de prueba — descarga datos de Citibike y los sube a GCS.

Uso:
    python -m ingestion.run_citibike                          # 2 meses atrás (default seguro)
    python -m ingestion.run_citibike --year 2024 --month 1   # mes específico
    python -m ingestion.run_citibike --dry-run                # descarga pero no sube a GCS

Nota: los archivos ZIP de Citibike pesan entre 50MB y 150MB.
El dry-run solo valida que el archivo existe y es descargable.
"""

import argparse
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    # Usamos enero 2025 como default seguro ya que sabemos que está disponible.
    # En producción Airflow pasará el mes explícitamente.
    default_year = 2025
    default_month = 1

    parser = argparse.ArgumentParser(description="Citibike extractor runner")
    parser.add_argument("--year", type=int, default=default_year)
    parser.add_argument("--month", type=int, default=default_month)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Descarga el archivo pero no lo sube a GCS.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from ingestion.extractors.citibike_extractor import CitibikeExtractor

    extractor = CitibikeExtractor()

    print(f"Downloading Citibike data for {args.year}-{args.month:02d}...")
    content, filename = extractor.extract(year=args.year, month=args.month)

    if args.dry_run:
        print(f"\n--- DRY RUN — archivo descargado (no subido a GCS) ---")
        print(f"Filename : {filename}")
        print(f"Size     : {len(content) / 1024 / 1024:.1f} MB")
        return

    from ingestion.loaders.gcs_loader import GCSLoader

    bucket_name = os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr")
    loader = GCSLoader(bucket_name=bucket_name)
    uri = loader.load_bytes(
        content=content,
        source_name=extractor.source_name,
        year=args.year,
        month=args.month,
        filename=filename,
    )
    print(f"\n✅ Datos subidos correctamente a: {uri}")


if __name__ == "__main__":
    main()