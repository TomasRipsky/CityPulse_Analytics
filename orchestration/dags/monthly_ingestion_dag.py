"""
DAG de ingesta y procesamiento mensual — Citibike NYC.

Se ejecuta el día 8 de cada mes:
1. Descarga el ZIP mensual de Citibike desde S3 (Bronze)
2. Descomprime, limpia y tipea los datos (Silver)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "citypulse",
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}

REPO_PATH = "/home/usuario/citypulse_analytics"
BUCKET    = "city-pulse-tr"


def _sync_repo():
    import subprocess
    subprocess.run(["git", "-C", REPO_PATH, "pull"], check=True)


def _target_month(execution_date):
    """Calcula el mes objetivo: 2 meses antes de la ejecución."""
    month_offset = execution_date.month - 2
    if month_offset <= 0:
        return execution_date.year - 1, 12 + month_offset
    return execution_date.year, month_offset


def extract_citibike(**context):
    _sync_repo()
    import sys
    sys.path.insert(0, REPO_PATH)

    from ingestion.extractors.citibike_extractor import CitibikeExtractor
    from ingestion.loaders.gcs_loader import GCSLoader

    year, month = _target_month(context["logical_date"])
    print(f"Extracting Citibike data for {year}-{month:02d}")

    extractor = CitibikeExtractor()
    content, filename = extractor.extract(year=year, month=month)

    loader = GCSLoader(bucket_name=BUCKET)
    uri = loader.load_bytes(content=content, source_name=extractor.source_name, year=year, month=month, filename=filename)
    print(f"✅ Bronze: {uri}")
    return uri


def process_citibike(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from processing.processors.citibike_processor import CitibikeProcessor
    from processing.loaders.gcs_silver_loader import GCSSilverLoader

    year, month = _target_month(context["logical_date"])

    processor = CitibikeProcessor(bucket_name=BUCKET)
    df = processor.process_month(year=year, month=month)

    loader = GCSSilverLoader(bucket_name=BUCKET)
    uri = loader.load_monthly(df=df, source_name=processor.source_name, year=year, month=month)
    print(f"✅ Silver: {uri} ({len(df)} rows)")
    return uri


with DAG(
    dag_id="prod.monthly_ingestion",
    description="Ingesta y procesamiento mensual de Citibike NYC",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 8 * *",
    catchup=False,
    tags=["ingestion", "processing", "monthly", "prod"],
) as dag:

    t_extract = PythonOperator(task_id="extract_citibike", python_callable=extract_citibike)
    t_process = PythonOperator(task_id="process_citibike", python_callable=process_citibike)

    t_extract >> t_process