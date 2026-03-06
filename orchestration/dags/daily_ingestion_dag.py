"""
DAG de ingesta diaria — Clima y Calidad del Aire.

Ejecuta cada día a las 6:00 AM UTC los extractores de
Open-Meteo Forecast y Open-Meteo Air Quality para NYC.

Las tareas corren en paralelo ya que son independientes entre sí.
Si una falla, la otra continúa y Airflow reintenta la fallida
automáticamente según la política de reintentos definida.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Argumentos por defecto aplicados a todas las tareas del DAG.
# retries=2 significa que si una tarea falla, Airflow la reintenta
# hasta 2 veces con 5 minutos de espera entre intentos.
default_args = {
    "owner": "citypulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

# ─────────────────────────────────────────────
# Funciones de cada tarea
# Importamos los extractores dentro de la función para evitar
# problemas de importación al parsear el DAG.
# ─────────────────────────────────────────────

def extract_weather(**context):
    """Extrae datos de clima para la fecha de ejecución del DAG."""
    import sys
    sys.path.insert(0, "/home/usuario/citypulse_analytics")

    from datetime import date
    import subprocess
    subprocess.run(
        ["git", "-C", "/home/usuario/citypulse_analytics", "pull"],
        check=True
    )

    from ingestion.extractors.weather_extractor import WeatherExtractor
    from ingestion.loaders.gcs_loader import GCSLoader
    import os

    # logical_date es la fecha de ejecución lógica del DAG.
    # Para el DAG de ayer ejecutado hoy, logical_date = ayer.
    execution_date = context["logical_date"].date()

    extractor = WeatherExtractor()
    data = extractor.extract(execution_date)

    loader = GCSLoader(bucket_name=os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr"))
    uri = loader.load(data=data, source_name=extractor.source_name, extraction_date=execution_date)

    print(f"✅ Weather data uploaded to: {uri}")
    return uri


def extract_air_quality(**context):
    """Extrae datos de calidad del aire para la fecha de ejecución del DAG."""
    import sys
    sys.path.insert(0, "/home/usuario/citypulse_analytics")

    from datetime import date
    import subprocess
    subprocess.run(
        ["git", "-C", "/home/usuario/citypulse_analytics", "pull"],
        check=True
    )

    from ingestion.extractors.air_quality_extractor import AirQualityExtractor
    from ingestion.loaders.gcs_loader import GCSLoader
    import os

    execution_date = context["logical_date"].date()

    extractor = AirQualityExtractor()
    data = extractor.extract(execution_date)

    loader = GCSLoader(bucket_name=os.environ.get("GCP_BUCKET_NAME", "city-pulse-tr"))
    uri = loader.load(data=data, source_name=extractor.source_name, extraction_date=execution_date)

    print(f"✅ Air quality data uploaded to: {uri}")
    return uri


# ─────────────────────────────────────────────
# Definición del DAG
# ─────────────────────────────────────────────

with DAG(
    dag_id="daily_ingestion",
    description="Ingesta diaria de clima y calidad del aire para NYC",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 6 * * *",  # Cada día a las 6:00 AM UTC
    catchup=False,                  # No ejecutar fechas pasadas al activar el DAG
    tags=["ingestion", "daily", "weather", "air_quality"],
) as dag:

    weather_task = PythonOperator(
        task_id="extract_weather",
        python_callable=extract_weather,
    )

    air_quality_task = PythonOperator(
        task_id="extract_air_quality",
        python_callable=extract_air_quality,
    )

    # Las dos tareas corren en paralelo — no hay dependencia entre ellas
    [weather_task, air_quality_task]