"""
GCS Silver Loader — guarda DataFrames como Parquet en la capa Silver.

Responsabilidad única: dado un DataFrame y una fecha, serializar
a Parquet y subir a GCS Silver con la ruta de particionado correcta.

¿Por qué Parquet?
- Formato columnar: lecturas analíticas 10x más rápidas que CSV
- Compresión nativa: ocupa 5-10x menos que CSV o JSON
- Tipos de datos garantizados: las fechas son fechas, no strings
- Compatible con BigQuery, Spark y cualquier motor analítico
"""

import logging
from datetime import date
from io import BytesIO

import pandas as pd
from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSSilverLoader:
    """
    Sube DataFrames en formato Parquet a GCS Silver.

    Estructura de destino:
        silver/{source}/year={Y}/month={MM}/day={DD}/{source}_{YYYYMMDD}.parquet
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def load(self, df: pd.DataFrame, source_name: str, processing_date: date) -> str:
        """
        Serializa el DataFrame a Parquet y lo sube a GCS Silver.
        Devuelve la URI completa del archivo subido.
        """
        gcs_path = self._build_path(source_name, processing_date)

        # Serializamos a Parquet en memoria — no necesitamos escribir
        # en disco local, lo subimos directamente desde RAM a GCS.
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
        buffer.seek(0)

        blob = self.bucket.blob(gcs_path)
        blob.upload_from_file(buffer, content_type="application/octet-stream")

        full_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {len(df)} rows to {full_uri}")
        return full_uri

    def load_monthly(self, df: pd.DataFrame, source_name: str, year: int, month: int) -> str:
        """
        Versión mensual del loader para Citibike.
        No tiene partición por día porque los datos son mensuales.
        """
        gcs_path = f"silver/{source_name}/year={year}/month={month:02d}/{source_name}_{year}{month:02d}.parquet"

        buffer = BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
        buffer.seek(0)

        blob = self.bucket.blob(gcs_path)
        blob.upload_from_file(buffer, content_type="application/octet-stream")

        full_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {len(df)} rows to {full_uri}")
        return full_uri

    def _build_path(self, source_name: str, processing_date: date) -> str:
        return (
            f"silver/{source_name}/"
            f"year={processing_date.year}/"
            f"month={processing_date.month:02d}/"
            f"day={processing_date.day:02d}/"
            f"{source_name}_{processing_date.strftime('%Y%m%d')}.parquet"
        )