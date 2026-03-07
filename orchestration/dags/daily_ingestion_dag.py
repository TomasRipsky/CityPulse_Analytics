"""
DAG de ingesta, procesamiento y carga diario — Clima y Calidad del Aire.

Ejecuta cada día a las 6:00 AM UTC:
1. Extrae datos de las APIs (Bronze)
2. Procesa y limpia los datos (Silver)
3. Carga a BigQuery Staging

Las dos fuentes corren en paralelo entre sí pero cada una
respeta el orden extracción → procesamiento → carga.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "citypulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

REPO_PATH  = "/home/usuario/citypulse_analytics"
BUCKET     = "city-pulse-tr"
PROJECT_ID = "project-6c4733db-2f24-496d-90f"


def _sync_repo():
    import subprocess
    subprocess.run(["git", "-C", REPO_PATH, "pull"], check=True)


def extract_weather(**context):
    _sync_repo()
    import sys
    sys.path.insert(0, REPO_PATH)

    from ingestion.extractors.weather_extractor import WeatherExtractor
    from ingestion.loaders.gcs_loader import GCSLoader

    execution_date = context["logical_date"].date()
    extractor = WeatherExtractor()
    data = extractor.extract(execution_date)

    loader = GCSLoader(bucket_name=BUCKET)
    uri = loader.load(data=data, source_name=extractor.source_name, extraction_date=execution_date)
    print(f"✅ Bronze: {uri}")
    return uri


def process_weather(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from processing.processors.weather_processor import WeatherProcessor
    from processing.loaders.gcs_silver_loader import GCSSilverLoader

    execution_date = context["logical_date"].date()
    processor = WeatherProcessor(bucket_name=BUCKET)
    df = processor.process(execution_date)

    loader = GCSSilverLoader(bucket_name=BUCKET)
    uri = loader.load(df=df, source_name=processor.source_name, processing_date=execution_date)
    print(f"✅ Silver: {uri} ({len(df)} rows)")
    return uri


def load_weather(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from loading.loaders.weather_loader import WeatherLoader

    execution_date = context["logical_date"].date()
    loader = WeatherLoader(project_id=PROJECT_ID, bucket_name=BUCKET)
    rows = loader.load(loading_date=execution_date)
    print(f"✅ BigQuery: {rows} rows loaded for {execution_date}")
    return rows


def extract_air_quality(**context):
    _sync_repo()
    import sys
    sys.path.insert(0, REPO_PATH)

    from ingestion.extractors.air_quality_extractor import AirQualityExtractor
    from ingestion.loaders.gcs_loader import GCSLoader

    execution_date = context["logical_date"].date()
    extractor = AirQualityExtractor()
    data = extractor.extract(execution_date)

    loader = GCSLoader(bucket_name=BUCKET)
    uri = loader.load(data=data, source_name=extractor.source_name, extraction_date=execution_date)
    print(f"✅ Bronze: {uri}")
    return uri


def process_air_quality(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from processing.processors.air_quality_processor import AirQualityProcessor
    from processing.loaders.gcs_silver_loader import GCSSilverLoader

    execution_date = context["logical_date"].date()
    processor = AirQualityProcessor(bucket_name=BUCKET)
    df = processor.process(execution_date)

    loader = GCSSilverLoader(bucket_name=BUCKET)
    uri = loader.load(df=df, source_name=processor.source_name, processing_date=execution_date)
    print(f"✅ Silver: {uri} ({len(df)} rows)")
    return uri


def load_air_quality(**context):
    import sys
    sys.path.insert(0, REPO_PATH)

    from loading.loaders.air_quality_loader import AirQualityLoader

    execution_date = context["logical_date"].date()
    loader = AirQualityLoader(project_id=PROJECT_ID, bucket_name=BUCKET)
    rows = loader.load(loading_date=execution_date)
    print(f"✅ BigQuery: {rows} rows loaded for {execution_date}")
    return rows


with DAG(
    dag_id="prod.daily_ingestion",
    description="Ingesta, procesamiento y carga diaria de clima y calidad del aire para NYC",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 * * *",
    catchup=False,
    tags=["ingestion", "processing", "loading", "daily", "prod"],
) as dag:

    t_extract_weather     = PythonOperator(task_id="extract_weather",     python_callable=extract_weather)
    t_process_weather     = PythonOperator(task_id="process_weather",     python_callable=process_weather)
    t_load_weather        = PythonOperator(task_id="load_weather",        python_callable=load_weather)

    t_extract_air_quality = PythonOperator(task_id="extract_air_quality", python_callable=extract_air_quality)
    t_process_air_quality = PythonOperator(task_id="process_air_quality", python_callable=process_air_quality)
    t_load_air_quality    = PythonOperator(task_id="load_air_quality",    python_callable=load_air_quality)

    # Cada fuente respeta su orden pero ambas corren en paralelo
    t_extract_weather     >> t_process_weather     >> t_load_weather
    t_extract_air_quality >> t_process_air_quality >> t_load_air_quality