# One identity runs the pipeline. It can read and write the lake and the four datasets and run
# BigQuery jobs — nothing else in the project, and nothing about IAM.
resource "google_service_account" "pipeline" {
  account_id   = "citypulse-pipeline"
  display_name = "CityPulse pipeline (${var.env})"

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "pipeline_lake" {
  bucket = google_storage_bucket.lake.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.pipeline.member
}

resource "google_bigquery_dataset_iam_member" "pipeline_datasets" {
  for_each   = google_bigquery_dataset.layers
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.pipeline.member
}

resource "google_project_iam_member" "pipeline_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.pipeline.member
}

# Local runs (Airflow on a laptop, backfills) use the operator's own login to impersonate the
# pipeline account, so they get exactly its permissions and no key ever exists.
resource "google_service_account_iam_member" "operator_impersonation" {
  count              = var.operator == "" ? 0 : 1
  service_account_id = google_service_account.pipeline.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = var.operator
}

# --- CI (dev only): GitHub Actions builds each pull request's dbt models in throwaway datasets.
# Nothing in CI touches prod, so prod has no federation at all.

# CI creates and drops its own per-PR datasets; bigquery.user grants datasets.create.
resource "google_project_iam_member" "pipeline_ci_datasets" {
  count   = var.env == "dev" ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = google_service_account.pipeline.member
}

# Deleted pools stay reserved for 30 days: a suffix lets destroy → apply work immediately.
resource "random_id" "pool" {
  count       = var.env == "dev" ? 1 : 0
  byte_length = 2
}

# Right after the IAM API is enabled, creating a pool answers 403 for a minute or two.
resource "time_sleep" "iam_propagation" {
  count           = var.env == "dev" ? 1 : 0
  create_duration = "90s"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool" "github" {
  count                     = var.env == "dev" ? 1 : 0
  workload_identity_pool_id = "github-${random_id.pool[0].hex}"
  display_name              = "GitHub Actions"

  depends_on = [time_sleep.iam_propagation]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  count                              = var.env == "dev" ? 1 : 0
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Without a condition any GitHub repository could exchange tokens here. Only this repository's
  # citypulse-* workflows qualify, and only for the events CI uses — an allowlist, so a future
  # workflow on issue_comment, workflow_run or pull_request_target (which runs with the base
  # repository's identity on fork code) gets nothing. workflow_ref names the calling workflow file;
  # add a job_workflow_ref check if reusable workflows are ever called.
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${var.github_repository_id}'",
    "assertion.workflow_ref.startsWith('${var.github_repository}/.github/workflows/citypulse-')",
    "assertion.event_name in ['pull_request', 'push', 'workflow_dispatch']",
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "pipeline_wif" {
  count              = var.env == "dev" ? 1 : 0
  service_account_id = google_service_account.pipeline.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github[0].name}/attribute.repository/${var.github_repository}"
}
