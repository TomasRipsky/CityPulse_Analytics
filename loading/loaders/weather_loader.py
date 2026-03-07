"""
Weather loader — carga datos de clima desde GCS Silver a BigQuery Staging.

Estrategia: append incremental por fecha.
Antes de cargar elimina las filas del mismo día para evitar duplicados
en caso de reejecutar el pipeline para la misma fecha.
"""

from datetime import date

from google.cloud import bigquery

from loading.base_loader import BaseLoader


class WeatherLoader(BaseLoader):

    @property
    def source_name(self) -> str:
        return "weather"

    @property
    def table_id(self) -> str:
        return "weather"

    def load(self, loading_date: date) -> int:
        self.logger.info(f"Loading weather data for {loading_date}")

        # Eliminamos las filas del mismo día antes de cargar
        # para que el pipeline sea idempotente: si falla y se
        # reejcuta no acumulamos duplicados.
        self._delete_date_partition(loading_date)

        gcs_uri = (
            f"gs://{self.bucket_name}/silver/weather/"
            f"year={loading_date.year}/"
            f"month={loading_date.month:02d}/"
            f"day={loading_date.day:02d}/"
            f"weather_{loading_date.strftime('%Y%m%d')}.parquet"
        )

        rows_loaded = self._load_parquet_to_bq(
            gcs_uri=gcs_uri,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        self.logger.info(f"Weather loaded: {rows_loaded} rows for {loading_date}")
        return rows_loaded

    def _delete_date_partition(self, loading_date: date):
        """Elimina las filas existentes del día antes de recargar."""
        query = f"""
            DELETE FROM `{self.full_table_id}`
            WHERE date = '{loading_date}'
        """
        try:
            self.bq_client.query(query).result()
            self.logger.info(f"Deleted existing rows for {loading_date}")
        except Exception:
            # La tabla puede no existir aún en la primera carga
            self.logger.info(f"No existing rows to delete for {loading_date}")