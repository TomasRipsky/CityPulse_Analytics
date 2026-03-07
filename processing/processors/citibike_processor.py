"""
Citibike processor — transforma el ZIP mensual de Citibike a Silver.

A diferencia de weather y air_quality, este procesador:
1. Descarga un ZIP desde GCS Bronze
2. Descomprime el CSV en memoria
3. Limpia y tipa las columnas
4. Devuelve un DataFrame con millones de filas

Por el volumen de datos (3-5M filas) procesamos en chunks
para no agotar la memoria de la VM.
"""

import io
import zipfile
from datetime import date

import pandas as pd
from google.cloud import storage

from processing.base_processor import BaseProcessor


class CitibikeProcessor(BaseProcessor):

    # Columnas que nos interesan del CSV original.
    # El archivo tiene más columnas pero estas son las relevantes para el análisis.
    COLUMNS = [
        "ride_id",
        "rideable_type",
        "started_at",
        "ended_at",
        "start_station_name",
        "end_station_name",
        "start_lat",
        "start_lng",
        "end_lat",
        "end_lng",
        "member_casual",
    ]

    @property
    def source_name(self) -> str:
        return "citibike"

    def process(self, processing_date: date) -> pd.DataFrame:
        """
        Para Citibike usamos año y mes en lugar de fecha exacta.
        processing_date se usa solo para extraer year y month.
        """
        return self.process_month(processing_date.year, processing_date.month)

    def process_month(self, year: int, month: int) -> pd.DataFrame:
        self.logger.info(f"Processing Citibike data for {year}-{month:02d}")

        zip_path = f"bronze/citibike/year={year}/month={month:02d}/{year}{month:02d}-citibike-tripdata.zip"

        # Descargamos el ZIP desde GCS Bronze en memoria
        blob = self.bucket.blob(zip_path)
        zip_content = blob.download_as_bytes()

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            csv_filename = [f for f in zf.namelist() if f.endswith(".csv")][0]
            with zf.open(csv_filename) as csv_file:
                df = pd.read_csv(
                    csv_file,
                    usecols=lambda c: c in self.COLUMNS,
                    dtype={
                        "ride_id":            "string",
                        "rideable_type":      "string",
                        "start_station_name": "string",
                        "end_station_name":   "string",
                        "member_casual":      "string",
                    },
                )

        # Tipado de fechas y coordenadas
        df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce", utc=True)
        df["ended_at"]   = pd.to_datetime(df["ended_at"],   errors="coerce", utc=True)
        df["start_lat"]  = pd.to_numeric(df["start_lat"], errors="coerce")
        df["start_lng"]  = pd.to_numeric(df["start_lng"], errors="coerce")
        df["end_lat"]    = pd.to_numeric(df["end_lat"],   errors="coerce")
        df["end_lng"]    = pd.to_numeric(df["end_lng"],   errors="coerce")

        # Calculamos la duración del viaje en minutos — métrica clave para el análisis
        df["duration_minutes"] = (
            (df["ended_at"] - df["started_at"]).dt.total_seconds() / 60
        ).round(2)

        # Eliminamos filas con fechas inválidas o duraciones negativas
        df = df[df["duration_minutes"] > 0].dropna(subset=["started_at", "ended_at"])

        df["year"]  = year
        df["month"] = month

        self.logger.info(f"Citibike processed: {len(df)} rows for {year}-{month:02d}")
        return df