# -----------------------------------------------------------------------------
# Data Warehouse — BigQuery
# Creamos dos datasets: uno para datos en crudo cargados desde Silver (staging)
# y otro para los modelos finales de DBT (marts).
# Separar staging de marts es una convención estándar en DBT y facilita
# el control de acceso: staging solo para pipelines, marts para analistas.
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "staging" {
  dataset_id    = "citypulse_staging"
  friendly_name = "CityPulse - Staging"
  description   = "Datos cargados desde GCS Silver. Uso exclusivo de pipelines. No usar directamente en dashboards."
  location      = var.region

  # Sin expiración de tablas: el pipeline controla el ciclo de vida.
  labels = {
    project     = "citypulse"
    environment = var.environment
    layer       = "staging"
  }
}

resource "google_bigquery_dataset" "marts" {
  dataset_id    = "citypulse_marts"
  friendly_name = "CityPulse - Data Marts"
  description   = "Modelos analíticos construidos por DBT. Fuente de verdad para dashboards e informes."
  location      = var.region

  labels = {
    project     = "citypulse"
    environment = var.environment
    layer       = "marts"
  }
}
