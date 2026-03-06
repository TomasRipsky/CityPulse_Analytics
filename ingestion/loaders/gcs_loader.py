"""
GCS Loader — sube datos extraídos a la capa Bronze del Data Lake.

Responsabilidad única: dado un payload y una fecha, construir
la ruta de destino correcta y subir el archivo a GCS.
No sabe nada de APIs ni de transformaciones.
"""

import json
import logging
from datetime import date

from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSLoader:
    """
    Sube archivos a GCS siguiendo la estructura de particionado
    por fecha estándar del proyecto.

    Métodos:
    - load()       → para JSON (weather, air_quality)
    - load_bytes() → para binarios (citibike ZIP)
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def load(self, data: dict, source_name: str, extraction_date: date) -> str:
        """
        Serializa el dict a JSON y lo sube a GCS Bronze.
        Usado por los extractores de weather y air_quality.
        """
        gcs_path = self._build_json_path(source_name, extraction_date)

        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(
            data=json.dumps(data, indent=2, ensure_ascii=False),
            content_type="application/json",
        )

        full_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {source_name} data to {full_uri}")
        return full_uri

    def load_bytes(self, content: bytes, source_name: str, year: int, month: int, filename: str) -> str:
        """
        Sube contenido binario a GCS Bronze.
        Usado por el extractor de Citibike que trabaja a nivel mensual.
        """
        gcs_path = f"bronze/{source_name}/year={year}/month={month:02d}/{filename}"

        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(content, content_type="application/zip")

        full_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {filename} to {full_uri}")
        return full_uri

    def _build_json_path(self, source_name: str, extraction_date: date) -> str:
        """
        Construye la ruta de destino con particionado por fecha.

        El formato year=/month=/day= es compatible con Hive partitioning,
        lo que permite a BigQuery y Dataflow leer particiones específicas
        sin escanear todo el bucket.
        """
        return (
            f"bronze/{source_name}/"
            f"year={extraction_date.year}/"
            f"month={extraction_date.month:02d}/"
            f"day={extraction_date.day:02d}/"
            f"{source_name}_{extraction_date.strftime('%Y%m%d')}.json"
        )