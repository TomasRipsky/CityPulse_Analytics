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
7. [Procesamiento Silver](#procesamiento-silver)
8. [Orquestación con Airflow](#orquestación-con-airflow)
9. [CI/CD](#cicd)
10. [Fases del Proyecto](#fases-del-proyecto)

---

## Arquitectura

El proyecto sigue la **Arquitectura Medallion** (Bronze → Silver → Gold), un estándar
de la industria que separa claramente cada etapa del ciclo de vida del dato.

```
[Open-Meteo API]  [Air Quality API]  [Citibike S3]
        │                │                 │
        └────────────────┴─────────────────┘
                         │
                 [Airflow DAGs]
            GCP VM e2-micro — us-central1
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
[GCS Bronze]                     [GCS Bronze]
 JSON / ZIP crudo                 JSON / ZIP crudo
         │                               │
         ▼                               ▼
[GCS Silver]                     [GCS Silver]
 Parquet limpio                   Parquet limpio
         │                               │
         └───────────────┬───────────────┘
                         │
               [BigQuery — Staging]
                         │
                [DBT — Data Marts]
                         │
              [Looker Studio — Dashboard]
```

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Lenguaje | Python 3.11 | Extractores, procesadores |
| Orquestación | Apache Airflow 2.8.1 | Scheduling y dependencias |
| Infraestructura Airflow | GCP VM e2-micro | Hosting gratuito 24/7 |
| Data Lake | Google Cloud Storage | Capas Bronze y Silver |
| Formato Silver | Apache Parquet | Columnar, comprimido, tipado |
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
├── .github/workflows/deploy.yml
├── infrastructure/terraform/
│   ├── main.tf, variables.tf, outputs.tf
│   ├── gcs.tf, bigquery.tf, Iam.tf
│   ├── compute.tf, firewall.tf
├── ingestion/
│   ├── base_extractor.py
│   ├── run_weather.py, run_air_quality.py, run_citibike.py
│   ├── extractors/
│   │   ├── weather_extractor.py
│   │   ├── air_quality_extractor.py
│   │   └── citibike_extractor.py
│   ├── loaders/gcs_loader.py
│   └── requirements.txt
├── processing/
│   ├── base_processor.py
│   ├── run_weather.py, run_air_quality.py, run_citibike.py
│   ├── processors/
│   │   ├── weather_processor.py
│   │   ├── air_quality_processor.py
│   │   └── citibike_processor.py
│   ├── loaders/gcs_silver_loader.py
│   └── requirements.txt
├── orchestration/dags/
│   ├── daily_ingestion_dag.py
│   └── monthly_ingestion_dag.py
├── transformation/             # DBT (Fase 5)
├── .env                        # No se sube al repo
└── README.md
```

---

## Fuentes de Datos

### Open-Meteo Forecast
- **Qué provee**: temperatura, precipitación, viento y humedad horarios para NYC
- **Autenticación**: ninguna — sin API key / **Frecuencia**: diaria

### Open-Meteo Air Quality
- **Qué provee**: PM2.5, PM10, ozono e índice AQI horarios
- **Autenticación**: ninguna — sin API key / **Frecuencia**: diaria

### Citibike NYC Trip Data
- **Qué provee**: viajes en bicicleta — origen, destino, duración, tipo de usuario
- **Formato**: CSV comprimido en ZIP, S3 público de AWS
- **Frecuencia**: mensual (~6 semanas de retraso) / **Volumen**: 3-5M viajes/mes

---

## Setup Inicial

### Pre-requisitos
- Cuenta de GCP con proyecto creado
- Terraform >= 1.5.0 / Python 3.11 / Google Cloud SDK

### 1. Clonar el repositorio
```bash
git clone https://github.com/TomasRipsky/citypulse_analytics.git
cd citypulse-analytics
```

### 2. Variables de entorno locales
Crear `.env` en la raíz:
```bash
GCP_BUCKET_NAME=city-pulse-tr
GOOGLE_CLOUD_PROJECT=your-project-id
```

### 3. Autenticarse en GCP
```bash
gcloud auth application-default login
gcloud config set project your-project-id
```

### 4. Habilitar APIs de GCP
```bash
gcloud services enable \
  iam.googleapis.com iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com storage.googleapis.com \
  bigquery.googleapis.com compute.googleapis.com \
  --project=your-project-id
```

### 5. Desplegar infraestructura
```bash
cd infrastructure/terraform
terraform init && terraform plan && terraform apply
```

### 6. Permisos de bootstrap
```bash
gsutil iam ch \
  serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.admin \
  gs://BUCKET_NAME

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --project=PROJECT_ID
```

### 7. Workload Identity Federation

GitHub Actions obtiene tokens efímeros sin claves JSON gracias a
**Workload Identity Federation** — práctica recomendada por Google.

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="PROJECT_ID" --location="global"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" --location="global" \
  --workload-identity-pool="github-pool" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='USER/REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/USER/REPO"

gcloud iam workload-identity-pools providers describe github-provider \
  --project="PROJECT_ID" --location="global" \
  --workload-identity-pool="github-pool" --format="value(name)"
```

Variables en GitHub — Settings → Secrets and variables → Actions → Variables:

| Variable | Valor |
|----------|-------|
| `GCP_PROJECT_ID` | ID de tu proyecto GCP |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Output del comando describe |
| `GCP_SERVICE_ACCOUNT` | Email de la service account |

---

## Ingesta de Datos

```bash
pip install -r ingestion/requirements.txt
```

**Clima:** `python -m ingestion.run_weather [--dry-run] [--date YYYY-MM-DD]`

**Calidad del aire:** `python -m ingestion.run_air_quality [--dry-run] [--date YYYY-MM-DD]`

**Citibike:** `python -m ingestion.run_citibike [--dry-run] [--year YYYY --month MM]`

### Estructura en GCS Bronze
```
gs://city-pulse-tr/bronze/
├── weather/year=YYYY/month=MM/day=DD/weather_YYYYMMDD.json
├── air_quality/year=YYYY/month=MM/day=DD/air_quality_YYYYMMDD.json
└── citibike/year=YYYY/month=MM/YYYYMM-citibike-tripdata.zip
```

---

## Procesamiento Silver

Los procesadores leen los datos crudos de GCS Bronze, los limpian,
tipan y escriben en GCS Silver en formato **Parquet**.

### ¿Por qué Parquet?
- **Columnar**: lecturas analíticas 10x más rápidas que CSV
- **Compresión nativa**: ocupa 5-10x menos que JSON o CSV
- **Tipos garantizados**: fechas son fechas, números son números
- **Compatible** con BigQuery, Spark y cualquier motor analítico

### Instalar dependencias
```bash
pip install -r processing/requirements.txt
```

### Ejecutar los procesadores
Todos soportan `--dry-run` para validar sin escribir en GCS.

**Clima:**
```bash
python -m processing.run_weather --dry-run --date 2026-03-06
python -m processing.run_weather --date 2026-03-06
```

**Calidad del aire:**
```bash
python -m processing.run_air_quality --dry-run --date 2026-03-06
python -m processing.run_air_quality --date 2026-03-06
```

**Citibike:**
```bash
python -m processing.run_citibike --dry-run --year 2025 --month 1
python -m processing.run_citibike --year 2025 --month 1
```

### Transformaciones aplicadas en Silver

| Fuente | Transformaciones |
|--------|-----------------|
| Weather | Arrays horarios → filas, tipos Float64, columnas `date` y `location` |
| Air Quality | Arrays horarios → filas, tipos Float64/Int64, categoría AQI calculada |
| Citibike | Descompresión ZIP, selección de columnas, cálculo de `duration_minutes`, filtro de viajes inválidos |

### Estructura en GCS Silver
```
gs://city-pulse-tr/silver/
├── weather/year=YYYY/month=MM/day=DD/weather_YYYYMMDD.parquet
├── air_quality/year=YYYY/month=MM/day=DD/air_quality_YYYYMMDD.parquet
└── citibike/year=YYYY/month=MM/citibike_YYYYMM.parquet
```

---

## Orquestación con Airflow

Airflow corre en una **VM e2-micro de GCP (free tier)** como servicio
permanente gestionado por `systemd`.

### ¿Por qué VM y no Cloud Composer?
Cloud Composer cuesta ~375€/mes. La VM e2-micro es permanentemente gratuita
y suficiente gracias al swap de 4GB configurado.

### Configuración de la VM

**Conectarse:**
```bash
gcloud compute ssh citypulse-airflow --zone=us-central1-a --project=PROJECT_ID
```

**Añadir swap:**
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Instalar Airflow:**
```bash
sudo apt-get update -y && sudo apt-get install -y python3-pip python3-venv git
python3 -m venv ~/airflow-env && source ~/airflow-env/bin/activate
pip install "apache-airflow==2.8.1" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"
pip install -r ~/citypulse_analytics/ingestion/requirements.txt
pip install -r ~/citypulse_analytics/processing/requirements.txt
```

**Inicializar y crear usuario:**
```bash
export AIRFLOW_HOME=~/airflow
airflow db init
airflow users create --username admin --password admin \
  --firstname Tu --lastname Nombre --role Admin --email tu@email.com
```

**Configurar como servicio systemd:**
```bash
sudo nano /etc/systemd/system/airflow.service
```
```ini
[Unit]
Description=Airflow Standalone
After=network.target

[Service]
User=usuario
Environment=AIRFLOW_HOME=/home/usuario/airflow
Environment=AIRFLOW__CORE__LOAD_EXAMPLES=False
Environment=PATH=/home/usuario/airflow-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=GCP_BUCKET_NAME=city-pulse-tr
ExecStart=/home/usuario/airflow-env/bin/airflow standalone
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable airflow && sudo systemctl start airflow
```

### Conectar la VM con GitHub (Deploy Key)

GitHub eliminó la autenticación por usuario/contraseña en 2021.
Las **Deploy Keys** son claves SSH vinculadas exclusivamente a un repositorio.

```bash
ssh-keygen -t ed25519 -C "citypulse-airflow-vm" -f ~/.ssh/github_key -N ""
cat ~/.ssh/github_key.pub  # añadir en GitHub → Settings → SSH keys

cat >> ~/.ssh/config << 'SSHEOF'
Host github.com
  IdentityFile ~/.ssh/github_key
  User git
SSHEOF

ssh -T git@github.com
git clone git@github.com:TomasRipsky/citypulse_analytics.git
```

### Desplegar los DAGs

**Primera vez:**
```bash
mkdir -p ~/airflow/dags/prod ~/airflow/dags/dev
cp ~/citypulse_analytics/orchestration/dags/*.py ~/airflow/dags/prod/
```

**Actualizar tras un merge:**
```bash
cd ~/citypulse_analytics && git pull
cp orchestration/dags/*.py ~/airflow/dags/prod/
```

### Flujo de trabajo: dev vs prod

```
~/airflow/dags/
├── prod/    ← DAGs mergeados via PR, estables, schedule activo
└── dev/     ← DAGs en desarrollo, experimentales, siempre pausados
```

Los `dag_id` siguen la convención de prefijos:
```python
dag_id="prod.daily_ingestion"   # producción
dag_id="dev.mi_nuevo_dag"       # desarrollo
```

**Regla:** nunca editar archivos de `prod/` directamente en la VM.

#### Ciclo de vida de un DAG nuevo

```
1. Crear en VS Code (Remote SSH) → ~/airflow/dags/dev/mi_dag.py
2. Airflow lo detecta en ~30 segundos
3. Probar con Trigger manual desde la UI
4. Cuando funciona → copiar al repo → PR → merge → mover a prod/
```

Todo DAG en `dev/` debe incluir:
```python
with DAG(
    dag_id="dev.mi_nuevo_dag",
    is_paused_upon_creation=True,
    ...
) as dag:
```

#### Promover un DAG de dev a prod
```bash
gcloud compute scp \
  citypulse-airflow:/home/usuario/airflow/dags/dev/mi_dag.py \
  ./orchestration/dags/mi_dag.py \
  --zone=us-central1-a
```

### Conectar VS Code a la VM (Remote SSH)

**Remote SSH** permite editar archivos en la VM directamente desde VS Code,
ideal para iterar rápidamente en DAGs de desarrollo sin pasar por el ciclo de PR.

```bash
# Una sola vez en tu máquina local — configura el acceso SSH a todas las VMs de GCP
gcloud compute config-ssh --project=PROJECT_ID
```

Luego en VS Code: `Ctrl+Shift+P` → `Remote-SSH: Connect to Host` → `citypulse-airflow`

Abre la carpeta `/home/usuario/airflow/dags` y edita directamente.

### Acceder a la UI de Airflow

El puerto 8080 está bloqueado en redes domésticas. Usa el **túnel SSH**
cada vez que quieras ver la UI — mantén la terminal abierta mientras la usas:

```bash
gcloud compute ssh citypulse-airflow \
  --zone=us-central1-a --project=PROJECT_ID \
  --ssh-flag="-L 8080:localhost:8080" \
  --ssh-flag="-N"
```

Acceder a: `http://localhost:8080` — Credenciales: `admin` / `admin`

### DAGs de producción

| DAG | Schedule | Tareas |
|-----|----------|--------|
| `prod.daily_ingestion` | Cada día 6:00 AM UTC | extract_weather → process_weather / extract_air_quality → process_air_quality (en paralelo) |
| `prod.monthly_ingestion` | Día 8 de cada mes 6:00 AM UTC | extract_citibike → process_citibike |

---

## CI/CD

| Evento | Comportamiento |
|--------|---------------|
| Pull Request → `main` | `terraform plan` + comentario en el PR |
| Push a `main` | `terraform apply` — despliega en GCP |

Solo se activa con cambios en `infrastructure/terraform/`.

---

## Fases del Proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **1. Infraestructura** | Terraform, GCP, Service Account, CI/CD | ✅ Completada |
| **2. Ingesta** | Extractores Python, GCS Bronze | ✅ Completada |
| **3. Orquestación** | Airflow en GCP VM, DAGs automáticos | ✅ Completada |
| **4. Procesamiento** | Transformaciones Silver, Parquet | ✅ Completada |
| **5. Warehouse** | Carga a BigQuery Staging | ⏳ Pendiente |
| **6. Transformación** | Modelos DBT Gold layer | ⏳ Pendiente |
| **7. Visualización** | Dashboard en Looker Studio | ⏳ Pendiente |

---

*Proyecto de portfolio — Data Engineering*