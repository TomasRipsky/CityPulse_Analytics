"""
Weather extractor — Open-Meteo Forecast y Historical API.

Para fechas recientes (últimos 3 días) usa el endpoint de Forecast.
Para fechas históricas usa el endpoint de Archive, que tiene datos
desde 1940 y no tiene límite de fechas pasadas.

Documentación:
- Forecast: https://open-meteo.com/en/docs
- Historical: https://open-meteo.com/en/docs/historical-weather-api
"""

from datetime import date, timedelta

from ingestion.base_extractor import BaseExtractor

NYC_LATITUDE  = 40.7128
NYC_LONGITUDE = -74.0060
NYC_TIMEZONE  = "America/New_York"

# Open-Meteo Forecast solo devuelve datos fiables hasta 3 días atrás.
# Para fechas anteriores usamos el endpoint histórico.
FORECAST_LOOKBACK_DAYS = 3


class WeatherExtractor(BaseExtractor):

    FORECAST_URL  = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

    @property
    def source_name(self) -> str:
        return "weather"

    def extract(self, extraction_date: date) -> dict:
        self.logger.info(f"Extracting weather data for {extraction_date}")

        cutoff = date.today() - timedelta(days=FORECAST_LOOKBACK_DAYS)
        url = self.FORECAST_URL if extraction_date >= cutoff else self.HISTORICAL_URL

        self.logger.info(f"Using {'forecast' if url == self.FORECAST_URL else 'historical'} endpoint")

        date_str = extraction_date.strftime("%Y-%m-%d")

        raw = self._get(
            url=url,
            params={
                "latitude":   NYC_LATITUDE,
                "longitude":  NYC_LONGITUDE,
                "timezone":   NYC_TIMEZONE,
                "start_date": date_str,
                "end_date":   date_str,
                "hourly": [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "relative_humidity_2m",
                ],
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                ],
            },
        )

        raw["_metadata"] = {
            "extraction_date": date_str,
            "source": self.source_name,
            "location": "NYC",
        }

        self.logger.info(f"Weather data extracted successfully for {extraction_date}")
        return raw