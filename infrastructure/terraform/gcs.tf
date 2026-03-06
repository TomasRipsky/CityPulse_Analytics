# -----------------------------------------------------------------------------
# Data Lake — Google Cloud Storage
# Usamos un único bucket con prefijos por capa (bronze/, silver/).
# Esto simplifica la gestión de permisos y costes frente a múltiples buckets.
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "data_lake" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = false # Protección: evita borrado accidental con datos dentro

  # Versionado desactivado para ahorrar almacenamiento en free tier.
  # Lo activaremos si en el futuro necesitamos recuperación de archivos.
  versioning {
    enabled = false
  }

  # Lifecycle rule: archivos en bronze/ se eliminan tras 90 días.
  # Los datos crudos son efímeros; lo que importa es la capa silver y gold.
  lifecycle_rule {
    condition {
      age            = 90
      matches_prefix = ["bronze/"]
    }
    action {
      type = "Delete"
    }
  }

  # Uniform access: todos los permisos se gestionan via IAM, no ACLs por objeto.
  # Es la práctica recomendada por Google para nuevos buckets.
  uniform_bucket_level_access = true

  labels = {
    project     = "citypulse"
    environment = var.environment
    layer       = "datalake"
  }
}

# -----------------------------------------------------------------------------
# Carpetas lógicas del Data Lake
# GCS no tiene carpetas reales; creamos objetos vacíos como marcadores.
# Esto hace la estructura visible en la consola de GCP y en herramientas CLI.
# -----------------------------------------------------------------------------

resource "google_storage_bucket_object" "bronze_prefix" {
  name    = "bronze/.keep"
  bucket  = google_storage_bucket.data_lake.name
  content = "bronze layer"
}

resource "google_storage_bucket_object" "silver_prefix" {
  name    = "silver/.keep"
  bucket  = google_storage_bucket.data_lake.name
  content = "silver layer"
}
