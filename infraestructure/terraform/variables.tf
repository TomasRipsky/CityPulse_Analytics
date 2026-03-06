variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "project-6c4733db-2f24-496d-90f"
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "GCS bucket name for the Data Lake"
  type        = string
  default     = "city-pulse-tr"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}
