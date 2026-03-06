"""
Base extractor — clase padre de todos los extractores del proyecto.

Centraliza la lógica común: logging estructurado, reintentos con backoff
exponencial y un contrato claro que cada extractor hijo debe cumplir.
Así cada extractor específico solo contiene la lógica de su propia API.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Logging estructurado: incluye timestamp, nivel y nombre del extractor.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BaseExtractor(ABC):
    """
    Clase base para todos los extractores de CityPulse.

    Define el contrato que cada extractor debe cumplir:
    - extract(date) → dict con los datos crudos
    - source_name   → nombre identificador de la fuente

    También provee el método _get() con reintentos automáticos,
    que todos los extractores pueden usar sin reimplementar.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identificador de la fuente. Usado como prefijo en GCS Bronze."""
        pass

    @abstractmethod
    def extract(self, extraction_date: date) -> dict:
        """
        Extrae datos para una fecha concreta.
        Debe devolver un dict con los datos crudos listos para serializar a JSON.
        """
        pass

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _get(self, url: str, params: dict) -> dict:
        """
        GET con reintentos automáticos y backoff exponencial.

        Si la API falla (timeout, 5xx), reintenta hasta 3 veces
        esperando 2s, 4s y 8s entre intentos antes de fallar definitivamente.
        """
        self.logger.info(f"GET {url} | params={params}")
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()