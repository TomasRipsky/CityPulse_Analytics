output "lake_uri" {
  description = "Lake root for CITYPULSE_LAKE_URI."
  value       = "gs://${google_storage_bucket.lake.name}"
}

output "pipeline_service_account" {
  description = "Service account the pipeline runs as."
  value       = google_service_account.pipeline.email
}

output "workload_identity_provider" {
  description = "Provider resource name for google-github-actions/auth (dev only)."
  value       = var.env == "dev" ? google_iam_workload_identity_pool_provider.github[0].name : ""
}
