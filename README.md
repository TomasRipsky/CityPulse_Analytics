# CityPulse Analytics 🌆

> End-to-end data engineering pipeline que analiza la relación entre clima, calidad del aire y movilidad urbana en Nueva York.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Orquestación | Apache Airflow |
| Data Lake | Google Cloud Storage |
| Data Warehouse | BigQuery |
| Transformaciones | DBT Core |
| Infraestructura | Terraform |
| CI/CD | GitHub Actions |
| Lenguaje | Python 3.11 |

## Arquitectura

```
[Open-Meteo API]  [Air Quality API]  [Citibike S3]
        │                │                 │
        └────────────────┴─────────────────┘
                         │
                    [Airflow DAGs]
                         │
              [GCS Bronze — datos crudos]
                         │
              [GCS Silver — datos limpios]
                         │
               [BigQuery — Staging]
                         │
                [DBT — Data Marts]
                         │
              [Looker Studio — Dashboard]
```

## Estructura del Repositorio

```
citypulse-analytics/
├── .github/workflows/     # CI/CD con GitHub Actions
├── infrastructure/        # Terraform — infraestructura como código
├── ingestion/             # Extractores Python de APIs
├── orchestration/         # Airflow DAGs
├── transformation/        # Modelos DBT
└── docs/                  # Documentación y diagramas
```

## Setup

### Pre-requisitos
- Cuenta de GCP con proyecto creado
- Terraform >= 1.5.0
- Python 3.11
- Google Cloud SDK (`gcloud`)

### 1. Clonar el repositorio
```bash
git clone https://github.com/[tu-usuario]/citypulse-analytics.git
cd citypulse-analytics
```

### 2. Autenticarse en GCP
```bash
gcloud auth application-default login
```

### 3. Desplegar infraestructura
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

## Fuentes de Datos

- **Open-Meteo Forecast** — Temperatura, precipitación, viento (sin API key)
- **Open-Meteo Air Quality** — PM2.5, PM10, ozono (sin API key)
- **Citibike NYC Trip Data** — Histórico de viajes en bicicleta (S3 público)

---
*Proyecto de portfolio — Data Engineering*
