{% docs __overview__ %}

# CityPulse Analytics 🌆

Pipeline de datos end-to-end que analiza cómo el clima y la calidad del aire
afectan la movilidad urbana en Nueva York.

## Arquitectura de datos

```
Open-Meteo API → GCS Bronze (JSON) → GCS Silver (Parquet) → BigQuery Staging → DBT Gold → Looker Studio
Citibike S3    ↗                                                              ↗
```

## Capas

### Staging (vistas)
Vistas ligeras sobre las tablas raw de `citypulse_staging`. Solo castean tipos
y filtran nulos — sin lógica de negocio. Un modelo por fuente de datos.

### Marts (tablas)
Tablas con agregaciones analíticas en `citypulse_marts`, listas para Looker Studio.

| Modelo | Granularidad | Descripción |
|--------|-------------|-------------|
| `daily_weather_summary` | Diaria | Temperatura, precipitación, viento y humedad |
| `daily_air_quality_summary` | Diaria | AQI, PM2.5, PM10, ozono y categorías |
| `daily_mobility_summary` | Diaria | Viajes, duración, member vs casual, eléctrica vs clásica |
| `monthly_city_pulse` | Mensual | **Correlación** — une las tres fuentes para análisis cruzado |

## Fuentes de datos

- **Open-Meteo Forecast/Historical**: clima horario para NYC sin API key
- **Open-Meteo Air Quality**: calidad del aire horaria para NYC sin API key
- **Citibike Trip Data**: viajes mensuales en bici — S3 público de AWS (~6 semanas de retraso)

## Stack

Python 3.11 · Apache Airflow 2.8.1 · GCP (GCS + BigQuery + VM e2-micro) · Terraform · DBT Core 1.7

{% enddocs %}