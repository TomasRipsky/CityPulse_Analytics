"""
DAG de ingesta, procesamiento, carga y transformación mensual — Citibike NYC.

Se ejecuta el día 8 de cada mes a las 6:00 AM UTC:
1. Descarga el ZIP mensual de Citibike desde S3 (Bronze)
2. Descomprime, limpia y tipea los datos (Silver)
3. Carga a BigQuery Staging
4. Ejecuta dbt run para actualizar los marts Gold
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "citypulse",
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}

REPO_PATH  = "/home/usuario/citypulse_analytics"
BUCKET     = "city-pulse-tr"
PROJECT_ID = "project-6c4733db-2f24-496d-90f"
DBT_DIR    = f"{REPO_PATH}/transformation"
VENV_BIN   = "/home/usuario/airflow-env/bin"


def _sync_repo():
    import subprocess
    subprocess.run(["git", "-C", REPO_PATH, "pull"], check=True)


def _target_month(execution_date):
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


def load_citibike(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from loading.loaders.citibike_loader import CitibikeLoader

    year, month = _target_month(context["logical_date"])
    loader = CitibikeLoader(project_id=PROJECT_ID, bucket_name=BUCKET)
    rows = loader.load(year=year, month=month)
    print(f"✅ BigQuery: {rows} rows for {year}-{month:02d}")
    return rows


with DAG(
    dag_id="prod.monthly_ingestion",
    description="Ingesta, procesamiento, carga y transformación mensual de Citibike NYC",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 8 * *",
    catchup=False,
    tags=["ingestion", "processing", "loading", "dbt", "monthly", "prod"],
) as dag:

    t_extract = PythonOperator(task_id="extract_citibike", python_callable=extract_citibike)
    t_process = PythonOperator(task_id="process_citibike", python_callable=process_citibike)
    t_load    = PythonOperator(task_id="load_citibike",    python_callable=load_citibike)
    t_dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {VENV_BIN}/dbt run",
    )

    t_extract >> t_process >> t_load >> t_dbt_run