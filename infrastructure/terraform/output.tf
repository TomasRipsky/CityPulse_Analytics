output "data_lake_bucket" {
  description = "Nombre del bucket del Data Lake"
  value       = google_storage_bucket.data_lake.name
}

output "data_lake_url" {
  description = "URL del bucket del Data Lake"
  value       = "gs://${google_storage_bucket.data_lake.name}"
}

output "bigquery_staging_dataset" {
  description = "ID del dataset de staging en BigQuery"
  value       = google_bigquery_dataset.staging.dataset_id
}

output "bigquery_marts_dataset" {
  description = "ID del dataset de marts en BigQuery"
  value       = google_bigquery_dataset.marts.dataset_id
}
