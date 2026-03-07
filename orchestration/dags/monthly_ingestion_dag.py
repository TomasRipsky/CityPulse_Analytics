"""
DAG de ingesta mensual — Citibike NYC Trip Data.

Se ejecuta el día 8 de cada mes para descargar los datos
del mes anterior desde el S3 público de Citibike.

Usamos el día 8 como margen de seguridad: Citibike publica
los datos con un retraso de 4-6 semanas, por lo que en el
día 8 del mes N tenemos garantizados los datos del mes N-2.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "citypulse",
    "retries": 3,                       # Más reintentos por el tamaño del archivo
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def extract_citibike(**context):
    """
    Descarga datos de Citibike para 2 meses antes de la fecha de ejecución.
    Ejemplo: si el DAG corre en marzo 2026, descarga enero 2026.
    """
    import sys
    import subprocess
    sys.path.insert(0, "/home/usuario/citypulse_analytics")

    subprocess.run(
        ["git", "-C", "/home/usuario/citypulse_analytics", "pull"],
        check=True
    )

    from ingestion.extractors.citibike_extractor import CitibikeExtractor
    from ingestion.loaders.gcs_loader import GCSLoader
    import os

    # Calculamos el mes objetivo: 2 meses antes de la ejecución
    execution_date = context["logical_date"]
    month_offset = execution_date.month - 2
    if month_offset <= 0:
        target_year = execution_date.year - 1
        target_month = 12 + month_offset
    else:
        target_year = execution_date.year
        target_month = month_offset

    print(f"Downloading Citibike data for {target_year}-{target_month:02d}")

    extractor = CitibikeExtractor()
    content, filename = extractor.extract(year=target_year, month=target_month)

    loader = GCSLoader(bucket_name=os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr"))
    uri = loader.load_bytes(
        content=content,
        source_name=extractor.source_name,
        year=target_year,
        month=target_month,
        filename=filename,
    )

    print(f"✅ Citibike data uploaded to: {uri}")
    return uri


with DAG(
    dag_id="prod.monthly_ingestion",
    description="Ingesta mensual de datos de Citibike NYC",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 8 * *",  # Día 8 de cada mes a las 6:00 AM UTC
    catchup=False,
    tags=["ingestion", "monthly", "citibike"],
) as dag:

    citibike_task = PythonOperator(
        task_id="extract_citibike",
        python_callable=extract_citibike,
    )