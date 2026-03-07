"""
Base loader — clase padre de todos los loaders a BigQuery.

Responsabilidad: leer Parquet desde GCS Silver y cargarlo
en BigQuery Staging de forma incremental o con truncate.

Mismo patrón que BaseProcessor y BaseExtractor: centraliza
logging y el contrato común, cada loader hijo implementa
su lógica específica.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date

from google.cloud import bigquery, storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BaseLoader(ABC):
    """
    Clase base para todos los loaders de CityPulse.

    Define el contrato:
    - load(date)     → carga incremental diaria
    - source_name    → nombre identificador de la fuente
    - dataset_id     → dataset de destino en BigQuery
    - table_id       → tabla de destino en BigQuery
    """

    def __init__(self, project_id: str, bucket_name: str, dataset_id: str = "citypulse_staging"):
        self.project_id  = project_id
        self.bucket_name = bucket_name
        self.dataset_id  = dataset_id
        self.logger      = logging.getLogger(self.__class__.__name__)
        self.bq_client   = bigquery.Client(project=project_id)
        self.gcs_client  = storage.Client()

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @property
    @abstractmethod
    def table_id(self) -> str:
        pass

    @abstractmethod
    def load(self, **kwargs) -> int:
        """
        Carga los datos en BigQuery.
        Devuelve el número de filas cargadas.
        """
        pass

    @property
    def full_table_id(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    def _load_parquet_to_bq(self, gcs_uri: str, write_disposition: str) -> int:
        """
        Carga un archivo Parquet desde GCS a BigQuery.

        write_disposition puede ser:
        - WRITE_APPEND   → añade filas a la tabla existente
        - WRITE_TRUNCATE → borra la tabla y la recrea con los nuevos datos
        """
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=write_disposition,
            autodetect=True,
        )

        load_job = self.bq_client.load_table_from_uri(
            gcs_uri,
            self.full_table_id,
            job_config=job_config,
        )

        self.logger.info(f"Loading {gcs_uri} → {self.full_table_id} ({write_disposition})")
        load_job.result()  # espera a que el job termine

        table = self.bq_client.get_table(self.full_table_id)
        self.logger.info(f"Table {self.full_table_id} now has {table.num_rows} rows")
        return load_job.output_rows