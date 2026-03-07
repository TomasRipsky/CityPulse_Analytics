"""
Air quality processor — transforma datos crudos de calidad del aire a Silver.
"""

from datetime import date

import pandas as pd

from processing.base_processor import BaseProcessor


class AirQualityProcessor(BaseProcessor):

    @property
    def source_name(self) -> str:
        return "air_quality"

    def process(self, processing_date: date) -> pd.DataFrame:
        self.logger.info(f"Processing air quality data for {processing_date}")

        bronze_path = self._bronze_path(processing_date)
        raw = self._read_json(bronze_path)

        hourly = raw["hourly"]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(hourly["time"], utc=True),
            "pm2_5":     pd.array(hourly["pm2_5"],   dtype="Float64"),
            "pm10":      pd.array(hourly["pm10"],     dtype="Float64"),
            "ozone":     pd.array(hourly["ozone"],    dtype="Float64"),
            "us_aqi":    pd.array(hourly["us_aqi"],   dtype="Int64"),
        })

        df["date"]     = processing_date
        df["location"] = "NYC"
        df["aqi_category"] = df["us_aqi"].map(self._aqi_category)

        self.logger.info(f"Air quality processed: {len(df)} rows for {processing_date}")
        return df

    @staticmethod
    def _aqi_category(aqi) -> str:
        if pd.isna(aqi):
            return "Unknown"
        aqi = int(aqi)
        if aqi <= 50:   return "Good"
        if aqi <= 100:  return "Moderate"
        if aqi <= 150:  return "Unhealthy for Sensitive Groups"
        if aqi <= 200:  return "Unhealthy"
        if aqi <= 300:  return "Very Unhealthy"
        return "Hazardous"