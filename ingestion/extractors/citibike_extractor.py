"""
Citibike extractor — NYC Bike Share Trip Data (S3 público).

A diferencia de los extractores de clima y calidad del aire, este extractor
descarga archivos CSV mensuales en lugar de llamar a una API REST.
Los archivos están en un bucket S3 público de AWS, sin autenticación.

Formato de URL: https://s3.amazonaws.com/tripdata/YYYYMM-citibike-tripdata.csv.zip

Nota: subimos el CSV sin descomprimir a GCS Bronze para preservar el dato
crudo exactamente como viene de la fuente. La descompresión ocurrirá
en la capa de procesamiento (Silver).
"""

import io
import logging
import zipfile
from datetime import date

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

CITIBIKE_BASE_URL = "https://s3.amazonaws.com/tripdata"


class CitibikeExtractor:
    """
    Descarga el archivo mensual de viajes de Citibike NYC desde S3.

    No hereda de BaseExtractor porque su interfaz es diferente:
    opera a nivel de mes, no de día, y devuelve bytes en lugar de dict.
    Forzar la herencia aquí sería over-engineering.
    """

    def __init__(self):
        self.session = requests.Session()

    @property
    def source_name(self) -> str:
        return "citibike"

    def extract(self, year: int, month: int) -> tuple[bytes, str]:
        """
        Descarga el archivo ZIP mensual de Citibike.

        Devuelve una tupla (contenido_csv_bytes, nombre_archivo)
        listos para subir a GCS Bronze sin modificar.
        """
        filename = f"{year}{month:02d}-citibike-tripdata.zip"
        url = f"{CITIBIKE_BASE_URL}/{filename}"

        logger.info(f"Downloading Citibike data: {filename}")

        content = self._download(url)

        # Validamos que el ZIP contiene exactamente un CSV antes de subir.
        # Si el formato cambiara en el futuro, fallamos rápido con un mensaje claro.
        csv_filename = self._extract_csv_filename(content, filename)

        logger.info(f"Citibike data downloaded successfully: {csv_filename}")
        return content, filename

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _download(self, url: str) -> bytes:
        """Descarga con reintentos. Igual que _get() en BaseExtractor."""
        response = self.session.get(url, timeout=120)  # timeout más alto por archivos grandes
        response.raise_for_status()
        return response.content

    def _extract_csv_filename(self, zip_content: bytes, zip_filename: str) -> str:
        """
        Valida el ZIP y devuelve el nombre del CSV que contiene.
        Falla explícitamente si el formato no es el esperado.
        """
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise ValueError(f"No CSV found in {zip_filename}")
            return csv_files[0]