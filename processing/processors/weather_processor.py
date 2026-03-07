"""
Weather processor — transforma datos crudos de clima a Silver.

Lee el JSON horario de Open-Meteo desde Bronze y lo convierte
en un DataFrame con una fila por hora, limpio y bien tipado.
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

        # El JSON de Open-Meteo tiene arrays paralelos: un array de timestamps
        # y un array por cada variable. Los combinamos en un DataFrame tabular
        # donde cada fila es una hora del día.
        hourly = raw["hourly"]

        df = pd.DataFrame({
            "timestamp":          pd.to_datetime(hourly["time"]),
            "temperature_c":      pd.array(hourly["temperature_2m"],        dtype="Float64"),
            "precipitation_mm":   pd.array(hourly["precipitation"],         dtype="Float64"),
            "wind_speed_kmh":     pd.array(hourly["wind_speed_10m"],        dtype="Float64"),
            "humidity_pct":       pd.array(hourly["relative_humidity_2m"],  dtype="Float64"),
        })

        # Añadimos columnas de particionado explícitas — útiles para
        # filtros en BigQuery sin parsear el timestamp.
        df["date"]     = processing_date
        df["location"] = "NYC"

        self.logger.info(f"Weather processed: {len(df)} rows for {processing_date}")
        return df