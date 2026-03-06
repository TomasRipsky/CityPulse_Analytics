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

---

## Setup inicial — Guía completa

Esta sección documenta todos los pasos necesarios para reproducir el proyecto
desde cero en una cuenta nueva de GCP.

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

### 2. Autenticarse en GCP

```bash
gcloud auth application-default login
```

### 3. Habilitar las APIs de GCP

GCP requiere habilitar explícitamente cada API antes de poder usarla.
Este es un paso de bootstrap que se hace una única vez por proyecto.

```bash
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  --project=PROJECT_ID
```

### 4. Desplegar la infraestructura base

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

Si el bucket ya existe (creado manualmente), importarlo antes del apply:

```bash
terraform import google_storage_bucket.data_lake BUCKET_NAME
```

### 5. Permisos de bootstrap

Hay dos permisos que Terraform no puede darse a sí mismo y que deben
configurarse manualmente una única vez. Son previos a que el pipeline
funcione, por lo que no pueden gestionarse con código.

**Permiso para leer y escribir el estado de Terraform en GCS:**

```bash
gsutil iam ch \
  serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.admin \
  gs://BUCKET_NAME
```

**Permiso para gestionar roles IAM del proyecto:**

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"
```

### 6. Configurar el CI/CD con GitHub Actions

En lugar de usar claves JSON (un secreto estático que hay que rotar y
proteger), este proyecto usa **Workload Identity Federation**. Es la
práctica recomendada por Google y elimina por completo la necesidad
de gestionar credenciales.

#### ¿Por qué Workload Identity Federation?

El problema con las claves JSON es que son secretos de larga duración:
si se filtran o se comprometen, cualquiera puede operar en tu cuenta de
GCP indefinidamente. Workload Identity resuelve esto estableciendo una
relación de confianza directa entre GitHub y GCP, de forma que GitHub
Actions obtiene tokens de corta duración de forma automática, sin ningún
secreto de por medio.

```
Sin Workload Identity:
GitHub Actions → clave JSON estática → GCP
                 (secreto de larga duración, riesgo de filtración)

Con Workload Identity:
GitHub Actions → token OIDC efímero → GCP verifica con GitHub → acceso
                 (sin secretos, token expira en minutos)
```

#### Configuración paso a paso

**Crear el Workload Identity Pool:**

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

**Crear el Provider:**

```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='TU_USUARIO/TU_REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

La `--attribute-condition` es crítica: restringe el acceso únicamente
a tu repositorio. Sin ella, cualquier repositorio de GitHub podría
intentar autenticarse contra tu proyecto de GCP.

**Vincular la Service Account al Pool:**

```bash
gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --project="PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/TU_USUARIO/TU_REPO"
```

**Obtener el identificador del provider** (necesario para GitHub Actions):

```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

#### Variables en GitHub Actions

En **Settings → Secrets and variables → Actions → Variables**,
crear las siguientes variables:

| Variable | Valor |
|----------|-------|
| `GCP_PROJECT_ID` | ID de tu proyecto GCP |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Output del comando describe anterior |
| `GCP_SERVICE_ACCOUNT` | Email de la service account |

---

## CI/CD — Cómo funciona el pipeline

El pipeline de GitHub Actions gestiona el despliegue automático de
infraestructura. Funciona de forma diferente según el evento:

| Evento | Qué ejecuta |
|--------|-------------|
| Pull Request hacia `main` | Init → Format → Validate → **Plan** (publica resultado como comentario en el PR) |
| Push a `main` | Init → Format → Validate → Plan → **Apply** (despliega en GCP) |

El pipeline solo se activa si hay cambios dentro de `infrastructure/terraform/`.
Cambios en otras partes del repositorio no disparan un despliegue de infraestructura.

---

## Fuentes de Datos

| Fuente | Tipo | Autenticación |
|--------|------|---------------|
| Open-Meteo Forecast | REST, JSON | Sin API key |
| Open-Meteo Air Quality | REST, JSON | Sin API key |
| Citibike NYC Trip Data | CSV en S3 público | Sin autenticación |

---

*Proyecto de portfolio — Data Engineering*