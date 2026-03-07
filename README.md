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
7. [Orquestación con Airflow](#orquestación-con-airflow)
8. [CI/CD](#cicd)
9. [Fases del Proyecto](#fases-del-proyecto)

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

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Lenguaje | Python 3.11 | Extractores e ingesta |
| Orquestación | Apache Airflow 2.8.1 | Scheduling y dependencias |
| Infraestructura Airflow | GCP VM e2-micro | Hosting gratuito 24/7 |
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
├── orchestration/dags/
│   ├── daily_ingestion_dag.py
│   └── monthly_ingestion_dag.py
├── transformation/             # DBT (Fase 4)
├── .env                        # No se sube al repo
└── README.md
```

---

## Fuentes de Datos

### Open-Meteo Forecast
- **Qué provee**: temperatura, precipitación, viento y humedad horarios para NYC
- **Autenticación**: ninguna — sin API key
- **Frecuencia**: diaria

### Open-Meteo Air Quality
- **Qué provee**: PM2.5, PM10, ozono e índice AQI horarios
- **Autenticación**: ninguna — sin API key
- **Frecuencia**: diaria

### Citibike NYC Trip Data
- **Qué provee**: viajes en bicicleta de NYC — origen, destino, duración, tipo de usuario
- **Formato**: CSV comprimido en ZIP, S3 público de AWS
- **Frecuencia**: mensual (~6 semanas de retraso)
- **Volumen**: 3-5 millones de viajes/mes, 100-800MB por archivo
- **URL base**: `https://s3.amazonaws.com/tripdata/`

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
Permisos que Terraform no puede otorgarse a sí mismo. Se configuran una única vez.

```bash
# Acceso al bucket de estado de Terraform
gsutil iam ch serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com:roles/storage.admin gs://BUCKET_NAME

# Gestión de políticas IAM
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"

# Permisos de Compute
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

# Service Account User en la VM
gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:citypulse-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --project=PROJECT_ID
```

### 7. Workload Identity Federation

Este proyecto usa **Workload Identity Federation** en lugar de claves JSON.
Es la práctica recomendada por Google: GitHub Actions obtiene tokens efímeros
de corta duración sin necesidad de gestionar ningún secreto.

```
Sin Workload Identity:
GitHub Actions → clave JSON estática → GCP
                 (secreto de larga duración, riesgo de filtración)

Con Workload Identity:
GitHub Actions → token OIDC efímero → GCP verifica con GitHub → acceso
                 (sin secretos, token expira en minutos)
```

```bash
# Crear el pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="PROJECT_ID" --location="global" \
  --display-name="GitHub Actions Pool"

# Crear el provider (reemplaza USER/REPO)
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" --location="global" \
  --workload-identity-pool="github-pool" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='USER/REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Vincular la Service Account
gcloud iam service-accounts add-iam-policy-binding \
  citypulse-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/USER/REPO"

# Obtener el identificador del provider
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

El particionado `year=/month=/day=` sigue el estándar **Hive Partitioning**,
compatible con BigQuery para lecturas eficientes por rango de fechas.

---

## Orquestación con Airflow

Airflow corre en una **VM e2-micro de GCP (free tier)** como servicio
permanente gestionado por `systemd`. Arranca automáticamente con la VM
y se reinicia solo si falla.

### ¿Por qué VM y no Cloud Composer?
Cloud Composer tiene un coste de ~375€/mes. La VM e2-micro es **permanentemente
gratuita** en GCP y suficiente para este proyecto gracias al swap configurado.

### Configuración de la VM

**Conectarse:**
```bash
gcloud compute ssh citypulse-airflow --zone=us-central1-a --project=PROJECT_ID
```

**Añadir swap** — La VM e2-micro tiene 1GB de RAM, insuficiente para Airflow solo.
El swap reserva espacio en disco como memoria adicional para gestionar picos de uso:
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
```

**Inicializar y crear usuario admin:**
```bash
export AIRFLOW_HOME=~/airflow
airflow db init
airflow users create --username admin --password admin \
  --firstname Tu --lastname Nombre --role Admin --email tu@email.com
```

**Configurar como servicio systemd** — `systemd` garantiza que Airflow arranque
automáticamente con la VM y se reinicie solo si falla:
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

GitHub eliminó la autenticación por usuario/contraseña en 2021. La alternativa
recomendada son las **Deploy Keys**: claves SSH vinculadas exclusivamente a un
repositorio concreto, siguiendo el principio de mínimo privilegio — la VM puede
leer el código del proyecto pero no tiene acceso a ningún otro repositorio.

```
Sin Deploy Key:
VM → usuario/contraseña → GitHub  ❌ no soportado desde 2021

Con Deploy Key:
VM → clave SSH privada → GitHub verifica con clave pública → acceso al repo ✅
```

```bash
# Generar la clave en la VM
ssh-keygen -t ed25519 -C "citypulse-airflow-vm" -f ~/.ssh/github_key -N ""

# Ver la clave pública — copiarla y añadirla en GitHub
# Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/github_key.pub

# Configurar SSH para usar esa clave con GitHub
cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/github_key
  User git
EOF

# Verificar conexión
ssh -T git@github.com

# Clonar el repositorio
git clone git@github.com:TomasRipsky/citypulse_analytics.git

# Instalar dependencias
source ~/airflow-env/bin/activate
pip install -r ~/citypulse_analytics/ingestion/requirements.txt
```

### Desplegar los DAGs

**Primera vez:**
```bash
mkdir -p ~/airflow/dags
cp ~/citypulse_analytics/orchestration/dags/*.py ~/airflow/dags/
```

### Sincronización automática de DAGs

Para que los cambios en los DAGs lleguen a Airflow automáticamente sin
entrar a la VM, se puede configurar un cron job que sincroniza el repositorio, por ejemplo
cada 5 minutos:

```
git push a main → cron job en VM (cada 5 min) → git pull + cp → Airflow recarga
```

```bash
crontab -e
# Añadir al final:
*/5 * * * * cd /home/usuario/citypulse_analytics && git pull && cp orchestration/dags/*.py /home/usuario/airflow/dags/
```
(No se ha creado aun, no se percibe necesario aun debido a la simplicidad del proyecto)

### DAGs disponibles

| DAG | Schedule | Descripción |
|-----|----------|-------------|
| `daily_ingestion` | Cada día a las 6:00 AM UTC | Clima y calidad del aire en paralelo |
| `monthly_ingestion` | Día 8 de cada mes a las 6:00 AM UTC | Descarga Citibike con margen de publicación |

### Acceder a la UI de Airflow

El puerto 8080 está bloqueado en redes domésticas por el ISP. La solución
es un **túnel SSH**: redirige el puerto de la VM a tu máquina local a través
de SSH (puerto 22), que siempre está abierto.

```
Sin túnel: navegador → internet → puerto 8080 VM  ❌ bloqueado por ISP
Con túnel: navegador → localhost:8080 → SSH → VM → Airflow ✅
```

```bash
# Abrir el túnel (mantener la terminal abierta)
gcloud compute ssh citypulse-airflow \
  --zone=us-central1-a --project=PROJECT_ID \
  --ssh-flag="-L 8080:localhost:8080" \
  --ssh-flag="-N"
```

Acceder a: `http://localhost:8080` — Credenciales: `admin` / `admin`

> Los DAGs se ejecutan automáticamente aunque no tengas el túnel abierto.
> El túnel solo es necesario para ver la UI.

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
| **4. Procesamiento** | Transformaciones Silver layer | ⏳ Pendiente |
| **5. Warehouse** | Carga a BigQuery Staging | ⏳ Pendiente |
| **6. Transformación** | Modelos DBT Gold layer | ⏳ Pendiente |
| **7. Visualización** | Dashboard en Looker Studio | ⏳ Pendiente |

---

*Proyecto de portfolio — Data Engineering*