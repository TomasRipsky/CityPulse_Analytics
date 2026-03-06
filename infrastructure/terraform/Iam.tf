# -----------------------------------------------------------------------------
# Service Account — Identidad técnica del proyecto
# Esta cuenta será usada por GitHub Actions (CI/CD) y por los pipelines
# de datos para interactuar con GCP de forma segura y sin credenciales humanas.
# -----------------------------------------------------------------------------

resource "google_service_account" "citypulse_sa" {
  account_id   = "citypulse-sa"
  display_name = "CityPulse Service Account"
  description  = "Cuenta técnica para pipelines de datos y despliegues CI/CD"
}

# -----------------------------------------------------------------------------
# Permisos IAM — Principio de mínimo privilegio
# Cada rol tiene una justificación explícita. No usamos roles primitivos
# (Owner, Editor) porque son demasiado amplios y un riesgo de seguridad.
# -----------------------------------------------------------------------------

locals {
  sa_roles = [
    "roles/storage.objectAdmin",       # Leer y escribir objetos en GCS (Data Lake)
    "roles/bigquery.dataEditor",       # Leer y escribir datos en BigQuery
    "roles/bigquery.jobUser",          # Ejecutar queries en BigQuery (necesario para DBT)
    "roles/iam.serviceAccountTokenCreator", # Permitir que GitHub Actions se autentique
  ]
}

resource "google_project_iam_member" "citypulse_sa_roles" {
  for_each = toset(local.sa_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.citypulse_sa.email}"
}

# -----------------------------------------------------------------------------
# Output — Email de la Service Account
# Lo necesitaremos para configurar el secreto en GitHub Actions.
# -----------------------------------------------------------------------------

output "service_account_email" {
  description = "Email de la Service Account para configurar en GitHub Actions"
  value       = google_service_account.citypulse_sa.email
}
