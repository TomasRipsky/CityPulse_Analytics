"""
Base processor — clase padre de todos los procesadores Silver.

Responsabilidad: leer datos crudos de GCS Bronze, transformarlos
y devolver un DataFrame limpio y tipado listo para Silver.

Mismo patrón que BaseExtractor: centraliza logging y el contrato
común, cada procesador hijo solo implementa su lógica específica.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd
from google.cloud import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BaseProcessor(ABC):
    """
    Clase base para todos los procesadores de CityPulse.

    Define el contrato:
    - process(date) → DataFrame limpio y tipado
    - source_name   → nombre identificador de la fuente
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identificador de la fuente. Debe coincidir con el usado en Bronze."""
        pass

    @abstractmethod
    def process(self, processing_date: date) -> pd.DataFrame:
        """
        Lee el archivo Bronze de la fecha dada y devuelve
        un DataFrame limpio listo para Silver.
        """
        pass

    def _read_json(self, gcs_path: str) -> dict:
        """Lee un archivo JSON desde GCS y lo devuelve como dict."""
        import json
        blob = self.bucket.blob(gcs_path)
        content = blob.download_as_text()
        return json.loads(content)

    def _bronze_path(self, processing_date: date) -> str:
        """Construye la ruta Bronze estándar para una fecha dada."""
        return (
            f"bronze/{self.source_name}/"
            f"year={processing_date.year}/"
            f"month={processing_date.month:02d}/"
            f"day={processing_date.day:02d}/"
            f"{self.source_name}_{processing_date.strftime('%Y%m%d')}.json"
        )