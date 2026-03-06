"""
Weather extractor — Open-Meteo Forecast API.

Extrae datos meteorológicos diarios para Nueva York.
La API es gratuita, sin API key, con límite de 10.000 llamadas/día.
Documentación: https://open-meteo.com/en/docs
"""

from datetime import date

from ingestion.base_extractor import BaseExtractor

# Coordenadas de Nueva York (Central Park — punto de referencia estándar)
NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060
NYC_TIMEZONE = "America/New_York"


class WeatherExtractor(BaseExtractor):
    """
    Extrae temperatura, precipitación y viento diarios para NYC
    desde la API de Open-Meteo.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @property
    def source_name(self) -> str:
        return "weather"

    def extract(self, extraction_date: date) -> dict:
        """
        Extrae datos meteorológicos para una fecha concreta.

        Usamos el endpoint de forecast con start_date y end_date iguales
        para obtener exactamente un día. Esto nos permite también
        re-extraer fechas pasadas si fuera necesario (backfill).
        """
        self.logger.info(f"Extracting weather data for {extraction_date}")

        date_str = extraction_date.strftime("%Y-%m-%d")

        raw = self._get(
            url=self.BASE_URL,
            params={
                "latitude": NYC_LATITUDE,
                "longitude": NYC_LONGITUDE,
                "timezone": NYC_TIMEZONE,
                "start_date": date_str,
                "end_date": date_str,
                # Variables horarias: temperatura y precipitación hora a hora
                "hourly": [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "relative_humidity_2m",
                ],
                # Variables diarias: resumen del día
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                ],
            },
        )

        # Añadimos metadatos de extracción al payload crudo.
        # Esto nos permite saber cuándo y cómo se extrajo cada archivo
        # sin depender de metadatos externos.
        raw["_metadata"] = {
            "extraction_date": date_str,
            "source": self.source_name,
            "location": "NYC",
        }

        self.logger.info(f"Weather data extracted successfully for {extraction_date}")
        return raw
