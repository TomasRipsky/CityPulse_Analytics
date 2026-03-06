"""
Air Quality extractor — Open-Meteo Air Quality API.

Extrae datos de calidad del aire diarios para Nueva York.
Misma API base que el extractor de clima, distinto endpoint y variables.
Documentación: https://air-quality-api.open-meteo.com
"""

from datetime import date

from ingestion.base_extractor import BaseExtractor

# Mismas coordenadas que el extractor de clima para consistencia
NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060
NYC_TIMEZONE = "America/New_York"


class AirQualityExtractor(BaseExtractor):
    """
    Extrae PM2.5, PM10, ozono y índice de calidad del aire
    para NYC desde la API de Open-Meteo Air Quality.
    """

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    @property
    def source_name(self) -> str:
        return "air_quality"

    def extract(self, extraction_date: date) -> dict:
        """
        Extrae datos de calidad del aire para una fecha concreta.
        Misma estrategia que weather: start_date == end_date para
        obtener exactamente un día y permitir backfill.
        """
        self.logger.info(f"Extracting air quality data for {extraction_date}")

        date_str = extraction_date.strftime("%Y-%m-%d")

        raw = self._get(
            url=self.BASE_URL,
            params={
                "latitude": NYC_LATITUDE,
                "longitude": NYC_LONGITUDE,
                "timezone": NYC_TIMEZONE,
                "start_date": date_str,
                "end_date": date_str,
                "hourly": [
                    "pm2_5",           # Partículas finas — el indicador más relevante de salud
                    "pm10",            # Partículas gruesas
                    "ozone",           # Ozono troposférico
                    "us_aqi",          # Índice de calidad del aire (escala USA)
                ],
            },
        )

        raw["_metadata"] = {
            "extraction_date": date_str,
            "source": self.source_name,
            "location": "NYC",
        }

        self.logger.info(f"Air quality data extracted successfully for {extraction_date}")
        return raw