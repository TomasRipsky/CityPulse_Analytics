# CityPulse Analytics 🌆

> Pipeline de datos end-to-end que analiza la relación entre clima, calidad del aire
> y movilidad urbana en Nueva York — desde la ingesta hasta el dashboard.

[![Deploy Infrastructure](https://github.com/TomasRipsky/citypulse_analytics/actions/workflows/deploy.yml/badge.svg)](https://github.com/TomasRipsky/citypulse_analytics/actions/workflows/deploy.yml)

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Estructura del Repositorio](#estructura-del-repositorio)
4. [Fuentes de Datos](#fuentes-de-datos)
5. [Setup Inicial](#setup-inicial)
6. [Ingesta de Datos](#ingesta-de-datos)
7. [CI/CD](#cicd)
8. [Fases del Proyecto](#fases-del-proyecto)

---

## Arquitectura

El proyecto sigue la **Arquitectura Medallion** (Bronze → Silver → Gold), un estándar
de la industria que separa claramente cada etapa del ciclo de vida del dato.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                         │
│                                                                  │
│   Open-Meteo API        Air Quality API        Citibike S3      │
│   (clima horario)       (PM2.5, ozono)         (viajes NYC)     │
└──────────────┬──────────────────┬──────────────────┬────────────┘
               │                  │                  │
               └──────────────────┴──────────────────┘
                                  │
                          [Airflow DAGs]
                        Orquestación y scheduling
                                  │
               ┌──────────────────┴──────────────────┐
               │                                      │
               ▼                                      │
┌─────────────────────────┐                          │
│   GCS — Bronze Layer    │                          │
│   Datos crudos          │                          │
│   JSON / ZIP sin tocar  │                          │
└────────────┬────────────┘                          │
             │                                       │
             ▼                                       │
┌─────────────────────────┐                          │
│   GCS — Silver Layer    │                          │
│   Datos limpios         │                          │
│   Tipados y particionados│                         │
└────────────┬────────────┘                          │
             │                                       │
             ▼                                       │
┌─────────────────────────┐                          │
│   BigQuery — Staging    │◄─────────────────────────┘
│   Carga desde Silver    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   DBT — Gold Layer      │
│   Modelos analíticos    │
│   Data Marts            │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Looker Studio         │
│   Dashboard público     │
└─────────────────────────┘
```

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Lenguaje | Python 3.11 | Extractores e ingesta |
| Orquestación | Apache Airflow | Scheduling y dependencias |
| Data Lake | Google Cloud Storage | Capas Bronze y Silver |
| Data Warehouse | BigQuery | Capa Gold y consultas analíticas |
| Transformaciones | DBT Core | Modelos y tests de calidad |
| Infraestructura | Terraform | Infraestructura como código |
| CI/CD | GitHub Actions | Despliegue automático a GCP |
| Autenticación | Workload Identity Federation | Sin claves JSON |
| Visualización | Looker Studio | Dashboard público |

---

## Estructura del Repositorio

```
citypulse-analytics/
│
├── .github/
│   └── workflows/
│       └── deploy.yml              # Pipeline CI/CD
│
├── infrastructure/
│   └── terraform/
│       ├── main.tf                 # Provider y backend
│       ├── variables.tf            # Variables parametrizadas
│       ├── gcs.tf                  # Data Lake (GCS)
│       ├── bigquery.tf             # Data Warehouse (BigQuery)
│       ├── Iam.tf                  # Service Account y permisos
│       └── outputs.tf              # Outputs útiles
│
├── ingestion/
│   ├── base_extractor.py           # Clase base con reintentos y logging
│   ├── run_weather.py              # Runner — extractor de clima
│   ├── run_air_quality.py          # Runner — extractor de calidad del aire
│   ├── run_citibike.py             # Runner — extractor de Citibike
│   ├── extractors/
│   │   ├── weather_extractor.py    # Open-Meteo Forecast
│   │   ├── air_quality_extractor.py# Open-Meteo Air Quality
│   │   └── citibike_extractor.py   # Citibike NYC Trip Data
│   ├── loaders/
│   │   └── gcs_loader.py           # Subida a GCS Bronze
│   └── requirements.txt
│
├── orchestration/                  # Airflow DAGs (Fase 3)
├── transformation/                 # Modelos DBT (Fase 4)
│
├── .env                            # Variables locales (no se sube al repo)
├── .gitignore
└── README.md
```

---

## Fuentes de Datos

### 🌤 Open-Meteo Forecast
- **Qué provee**: temperatura, precipitación, viento y humedad horarios para NYC
- **Formato**: JSON via REST
- **Autenticación**: ninguna, sin API key
- **Frecuencia de extracción**: diaria
- **Documentación**: [open-meteo.com/en/docs](https://open-meteo.com/en/docs)

### 🌫 Open-Meteo Air Quality
- **Qué provee**: PM2.5, PM10, ozono e índice de calidad del aire (AQI) horarios
- **Formato**: JSON via REST
- **Autenticación**: ninguna, sin API key
- **Frecuencia de extracción**: diaria
- **Documentación**: [open-meteo.com/en/docs#air_quality](https://open-meteo.com/en/docs#air_quality)

### 🚲 Citibike NYC Trip Data
- **Qué provee**: todos los viajes en bicicleta de NYC — origen, destino, duración, tipo de usuario
- **Formato**: CSV comprimido en ZIP, publicado en S3 público de AWS
- **Autenticación**: ninguna
- **Frecuencia de extracción**: mensual (datos disponibles con ~6 semanas de retraso)
- **Volumen**: 3-5 millones de viajes/mes, archivos de 100-800MB
- **Histórico disponible**: desde 2013
- **URL base**: `https://s3.amazonaws.com/tripdata/`

---

## Setup Inicial

### Pre-requisitos

- Cuenta de GCP con proyecto creado
- Terraform >= 1.5.0
- Python 3.11
- Google Cloud SDK (`gcloud`)

### 1. Clonar el repositorio

```bash
git clone https://github.com/TomasRipsky/citypulse_analytics.git
cd citypulse-analytics
```

### 2. Configurar variables de entorno locales

Crear un archivo `.env` en la raíz del proyecto:

```bash
GCP_BUCKET_NAME=city-pulse-tr
GOOGLE_CLOUD_PROJECT=your-project-id
```

> ⚠️ El archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

### 3. Autenticarse en GCP

```bash
gcloud auth application-default login
gcloud config set project your-project-id
```

### 4. Habilitar las APIs de GCP

Este paso es obligatorio en cualquier proyecto nuevo de GCP.
Se realiza una única vez.

```bash
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  --project=your-project-id
```

### 5. Desplegar la infraestructura

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

> Si el bucket ya existía antes de ejecutar Terraform, importarlo primero:
> ```bash
> terraform import google_storage_bucket.data_lake BUCKET_NAME
> ```

### 6. Permisos de bootstrap

Dos permisos que deben configurarse manualmente una única vez, ya que
son previos al funcionamiento del pipeline y Terraform no puede
otorgárselos a sí mismo.

**Acceso de la Service Account al bucket de estado de Terraform:**

```bash
gsutil iam ch \
  serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.admin \
  gs://BUCKET_NAME
```

**Permiso para gestionar políticas IAM del proyecto:**

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"
```

### 7. Configurar CI/CD con Workload Identity Federation

Este proyecto usa **Workload Identity Federation** en lugar de claves JSON.
Es la práctica recomendada por Google: GitHub Actions obtiene tokens
efímeros de corta duración sin necesidad de gestionar ningún secreto.

```
Sin Workload Identity:
GitHub Actions → clave JSON estática → GCP
                 (secreto de larga duración, riesgo de filtración)

Con Workload Identity:
GitHub Actions → token OIDC efímero → GCP verifica con GitHub → acceso
                 (sin secretos, token expira en minutos)
```

**Crear el Workload Identity Pool:**

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

**Crear el Provider** (reemplaza `USER/REPO` con tus valores):

```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='USER/REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

**Vincular la Service Account al Pool:**

```bash
gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --project="PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/USER/REPO"
```

**Obtener el identificador del provider:**

```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

**Configurar variables en GitHub** — Settings → Secrets and variables → Actions → Variables:

| Variable | Valor |
|----------|-------|
| `GCP_PROJECT_ID` | ID de tu proyecto GCP |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Output del comando describe anterior |
| `GCP_SERVICE_ACCOUNT` | Email de la service account |

---

## Ingesta de Datos

Los extractores son scripts Python independientes, listos para ser
orquestados por Airflow en la Fase 3.

### Instalar dependencias

```bash
pip install -r ingestion/requirements.txt
```

### Ejecutar los extractores

Todos los extractores soportan `--dry-run` para validar sin escribir en GCS,
y `--date` / `--year` / `--month` para extraer fechas específicas (backfill).

**Clima (diario):**
```bash
python -m ingestion.run_weather --dry-run      # validar
python -m ingestion.run_weather                # extraer hoy
python -m ingestion.run_weather --date 2025-01-15  # backfill
```

**Calidad del aire (diario):**
```bash
python -m ingestion.run_air_quality --dry-run
python -m ingestion.run_air_quality
python -m ingestion.run_air_quality --date 2025-01-15
```

**Citibike (mensual):**
```bash
python -m ingestion.run_citibike --dry-run
python -m ingestion.run_citibike
python -m ingestion.run_citibike --year 2025 --month 1
```

### Estructura en GCS Bronze

```
gs://city-pulse-tr/
└── bronze/
    ├── weather/
    │   └── year=YYYY/month=MM/day=DD/
    │       └── weather_YYYYMMDD.json
    ├── air_quality/
    │   └── year=YYYY/month=MM/day=DD/
    │       └── air_quality_YYYYMMDD.json
    └── citibike/
        └── year=YYYY/month=MM/
            └── YYYYMM-citibike-tripdata.zip
```

> El particionado `year=/month=/day=` sigue el estándar **Hive Partitioning**,
> compatible con BigQuery y Dataflow para lecturas eficientes por rango de fechas.

---

## CI/CD

El pipeline de GitHub Actions gestiona el despliegue automático de infraestructura.

| Evento | Comportamiento |
|--------|---------------|
| Pull Request → `main` | Ejecuta `terraform plan` y publica el resultado como comentario en el PR |
| Push a `main` | Ejecuta `terraform apply` y despliega los cambios en GCP |

El pipeline **solo se activa** si hay cambios dentro de `infrastructure/terraform/`.
Cambios en extractores, DAGs o modelos DBT no disparan un despliegue de infraestructura.

---

## Fases del Proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **1. Infraestructura** | Terraform, GCP, Service Account, CI/CD | ✅ Completada |
| **2. Ingesta** | Extractores Python, GCS Bronze | ✅ Completada |
| **3. Orquestación** | Airflow DAGs, scheduling automático | 🔄 En progreso |
| **4. Procesamiento** | Transformaciones Silver layer | ⏳ Pendiente |
| **5. Warehouse** | Carga a BigQuery Staging | ⏳ Pendiente |
| **6. Transformación** | Modelos DBT Gold layer | ⏳ Pendiente |
| **7. Visualización** | Dashboard en Looker Studio | ⏳ Pendiente |

---

*Proyecto de portfolio — Data Engineering*