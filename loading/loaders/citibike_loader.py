"""
Citibike loader — carga datos de Citibike desde GCS Silver a BigQuery Staging.

Estrategia: truncate + reload mensual.
Los datos de Citibike son inmutables una vez publicados y el archivo
mensual se procesa completo, así que simplemente reemplazamos las
filas del mes en lugar de gestionar duplicados individualmente.

Usamos una tabla particionada por mes para que el WRITE_TRUNCATE
solo afecte al mes que estamos cargando y no a todo el histórico.
"""

from google.cloud import bigquery

from loading.base_loader import BaseLoader


class CitibikeLoader(BaseLoader):

    @property
    def source_name(self) -> str:
        return "citibike"

    @property
    def table_id(self) -> str:
        return "citibike"

    def load(self, year: int, month: int) -> int:
        self.logger.info(f"Loading Citibike data for {year}-{month:02d}")

        # Eliminamos el mes antes de recargar para garantizar idempotencia
        self._delete_month_partition(year, month)

        gcs_uri = (
            f"gs://{self.bucket_name}/silver/citibike/"
            f"year={year}/month={month:02d}/"
            f"citibike_{year}{month:02d}.parquet"
        )

        rows_loaded = self._load_parquet_to_bq(
            gcs_uri=gcs_uri,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        self.logger.info(f"Citibike loaded: {rows_loaded} rows for {year}-{month:02d}")
        return rows_loaded

    def _delete_month_partition(self, year: int, month: int):
        """Elimina todas las filas del mes antes de recargar."""
        query = f"""
            DELETE FROM `{self.full_table_id}`
            WHERE year = {year} AND month = {month}
        """
        try:
            self.bq_client.query(query).result()
            self.logger.info(f"Deleted existing rows for {year}-{month:02d}")
        except Exception:
            self.logger.info(f"No existing rows to delete for {year}-{month:02d}")