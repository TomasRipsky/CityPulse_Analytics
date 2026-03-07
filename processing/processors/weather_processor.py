"""
Weather processor — transforma datos crudos de clima a Silver.
"""

from datetime import date

import pandas as pd

from processing.base_processor import BaseProcessor


class WeatherProcessor(BaseProcessor):

    @property
    def source_name(self) -> str:
        return "weather"

    def process(self, processing_date: date) -> pd.DataFrame:
        self.logger.info(f"Processing weather data for {processing_date}")

        bronze_path = self._bronze_path(processing_date)
        raw = self._read_json(bronze_path)

        hourly = raw["hourly"]

        df = pd.DataFrame({
            # utc=True fuerza timezone UTC — PyArrow lo serializa como
            # TIMESTAMP en Parquet en lugar de INT64, evitando problemas
            # de conversión en BigQuery y DBT.
            "timestamp":          pd.to_datetime(hourly["time"], utc=True),
            "temperature_c":      pd.array(hourly["temperature_2m"],        dtype="Float64"),
            "precipitation_mm":   pd.array(hourly["precipitation"],         dtype="Float64"),
            "wind_speed_kmh":     pd.array(hourly["wind_speed_10m"],        dtype="Float64"),
            "humidity_pct":       pd.array(hourly["relative_humidity_2m"],  dtype="Float64"),
        })

        df["date"]     = processing_date
        df["location"] = "NYC"

        self.logger.info(f"Weather processed: {len(df)} rows for {processing_date}")
        return df