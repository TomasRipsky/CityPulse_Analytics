variable "env" {
  description = "Environment: dev (sample data, CI) or prod (the full dataset)."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be dev or prod."
  }
}

variable "project_id" {
  description = "GCP project created by `make bootstrap`."
  type        = string
}

variable "region" {
  description = "Region of the lake bucket and the BigQuery datasets (a GCS free-tier region)."
  type        = string
  default     = "us-central1"
}

variable "github_repository" {
  description = "owner/name of the repository whose workflows may use Workload Identity Federation."
  type        = string
  default     = "TomasRipsky/CityPulse_Analytics"
}

variable "github_repository_id" {
  description = "Immutable numeric id of that repository (a renamed or re-created repo gets a new one)."
  type        = string
  default     = "1174241884"
}

variable "operator" {
  description = "Principal allowed to run the pipeline locally as the pipeline service account, e.g. user:you@example.com. Empty: nobody."
  type        = string
  default     = ""
}

variable "query_quota_mib_per_day" {
  description = "Hard cap on BigQuery bytes scanned per day, in MiB, per environment. Together (70 GiB/day) they cap a month near 2 TiB: the free 1 TiB plus ~6 €, about the budgets' size."
  type        = map(number)
  default = {
    dev  = 20480 # 20 GiB: a full dbt build on the January 2025 sample scans ~1 GB; CI + local work
    prod = 51200 # 50 GiB: a full dbt build on 20 months reads ~18 GB
  }
}
