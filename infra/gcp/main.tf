locals {
  apis     = ["bigquery.googleapis.com", "storage.googleapis.com", "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com"]
  datasets = ["raw", "staging", "intermediate", "marts", "audit"]

  # Raw tables: one partition per ingested period, so a load replaces exactly one partition.
  raw_tables = {
    weather_hourly     = { partition = "DAY", field = "local_date", description = "Open-Meteo hourly weather for New York, one partition per New York day." }
    air_quality_hourly = { partition = "DAY", field = "local_date", description = "Open-Meteo hourly air quality for New York, one partition per New York day." }
    trips              = { partition = "MONTH", field = "source_month", description = "Every Citi Bike trip, one partition per monthly source file." }
  }
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# The lake can be rebuilt from the public sources, so destroy may delete it with its contents.
resource "google_storage_bucket" "lake" {
  name                        = "${var.project_id}-lake"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  # Soft delete would keep (and bill) every overwritten or deleted object for 7 days.
  soft_delete_policy {
    retention_duration_seconds = 0
  }

  # Trip ZIPs (400–700 MB each) are only needed until Silver is built; Silver is the copy we keep.
  lifecycle_rule {
    condition {
      age            = 30
      matches_prefix = ["bronze/citibike/"]
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_dataset" "layers" {
  for_each                   = toset(local.datasets)
  dataset_id                 = each.value
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_table" "raw" {
  for_each            = local.raw_tables
  dataset_id          = google_bigquery_dataset.layers["raw"].dataset_id
  table_id            = each.key
  description         = each.value.description
  schema              = file("${path.module}/schemas/${each.key}.json")
  deletion_protection = false

  time_partitioning {
    type  = each.value.partition
    field = each.value.field
  }
}

resource "google_bigquery_table" "load_audit" {
  dataset_id          = google_bigquery_dataset.layers["raw"].dataset_id
  table_id            = "load_audit"
  description         = "One row per load: rows the lake manifest promised and rows BigQuery wrote."
  schema              = file("${path.module}/schemas/load_audit.json")
  deletion_protection = false

  # Every load appends one row. An unpartitioned table accepts 1,500 modifications a day — fewer
  # than a full backfill (~1,240 loads) plus a retry; a partitioned one accepts 30,000.
  time_partitioning {
    type  = "MONTH"
    field = "loaded_at"
  }
}

# A budget alert only warns; this quota stops runaway queries.
resource "google_service_usage_consumer_quota_override" "bigquery_query_per_day" {
  provider       = google-beta
  service        = "bigquery.googleapis.com"
  metric         = urlencode("bigquery.googleapis.com/quota/query/usage")
  limit          = urlencode("/d/project")
  override_value = var.query_quota_mib_per_day[var.env]
  force          = true

  depends_on = [google_project_service.apis]
}
