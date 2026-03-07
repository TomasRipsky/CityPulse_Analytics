"""
Air quality loader — carga datos de calidad del aire desde GCS Silver a BigQuery Staging.

Estrategia: idéntica a weather, append incremental con delete previo por fecha.
"""

from datetime import date

from google.cloud import bigquery

from loading.base_loader import BaseLoader


class AirQualityLoader(BaseLoader):

    @property
    def source_name(self) -> str:
        return "air_quality"

    @property
    def table_id(self) -> str:
        return "air_quality"

    def load(self, loading_date: date) -> int:
        self.logger.info(f"Loading air quality data for {loading_date}")

        self._delete_date_partition(loading_date)

        gcs_uri = (
            f"gs://{self.bucket_name}/silver/air_quality/"
            f"year={loading_date.year}/"
            f"month={loading_date.month:02d}/"
            f"day={loading_date.day:02d}/"
            f"air_quality_{loading_date.strftime('%Y%m%d')}.parquet"
        )

        rows_loaded = self._load_parquet_to_bq(
            gcs_uri=gcs_uri,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        self.logger.info(f"Air quality loaded: {rows_loaded} rows for {loading_date}")
        return rows_loaded

    def _delete_date_partition(self, loading_date: date):
        query = f"""
            DELETE FROM `{self.full_table_id}`
            WHERE date = '{loading_date}'
        """
        try:
            self.bq_client.query(query).result()
            self.logger.info(f"Deleted existing rows for {loading_date}")
        except Exception:
            self.logger.info(f"No existing rows to delete for {loading_date}")