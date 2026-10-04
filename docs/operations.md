# Operations — as run from March to June 2026

How CityPulse was deployed and operated. Kept as a record; several steps are flagged by the
[audit](audit/2026-10-04-audit.md) and will change with the closing plan.

> [!WARNING]
> The bootstrap grants in step 4 give the service account `projectIamAdmin`, which lets it make
> itself project owner (audit H4). Do not reuse them as they are.

## 1. Prerequisites

GCP project with billing, `gcloud`, Terraform ≥ 1.5, Python 3.11. Local `.env` (never committed):

```bash
GCP_BUCKET_NAME=city-pulse-tr
GOOGLE_CLOUD_PROJECT=<project-id>
```

```bash
gcloud auth application-default login
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com storage.googleapis.com \
  bigquery.googleapis.com compute.googleapis.com --project=<project-id>
```

## 2. Terraform state bucket

`maint.tf` stores state in `gs://city-pulse-tr/terraform/state` — the same bucket Terraform
manages (audit M4). The bucket must exist before `terraform init`.

## 3. Infrastructure

```bash
cd infrastructure/terraform
terraform init && terraform plan && terraform apply
```

Creates the data-lake bucket (Bronze/Silver prefixes, 90-day Bronze lifecycle), the
`citypulse_staging` and `citypulse_marts` datasets, the `citypulse-sa` service account with
`storage.objectAdmin`, `bigquery.dataOwner`, `bigquery.jobUser` and
`iam.serviceAccountTokenCreator`, the `citypulse-airflow` e2-micro VM and a firewall rule for
ports 22 and 8080 from `var.my_ip`.

## 4. Bootstrap grants (manual)

```bash
SA=citypulse-sa@<project-id>.iam.gserviceaccount.com
gcloud storage buckets add-iam-policy-binding gs://<bucket> --member=serviceAccount:$SA --role=roles/storage.admin
gcloud projects add-iam-policy-binding <project-id> --member=serviceAccount:$SA --role=roles/resourcemanager.projectIamAdmin
gcloud projects add-iam-policy-binding <project-id> --member=serviceAccount:$SA --role=roles/compute.admin
gcloud iam service-accounts add-iam-policy-binding $SA --member=serviceAccount:$SA --role=roles/iam.serviceAccountUser
```

## 5. Workload Identity Federation for GitHub Actions

```bash
gcloud iam workload-identity-pools create github-pool --location=global --project=<project-id>
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global --workload-identity-pool=github-pool --project=<project-id> \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository \
  --attribute-condition="assertion.repository=='<owner>/<repo>'"
gcloud iam service-accounts add-iam-policy-binding $SA --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-pool/attribute.repository/<owner>/<repo>"
```

GitHub → Settings → Secrets and variables → Actions → **Variables**: `GCP_PROJECT_ID`,
`GCP_WORKLOAD_IDENTITY_PROVIDER` (the provider's full resource name), `GCP_SERVICE_ACCOUNT`.

## 6. Airflow on the VM

```bash
gcloud compute ssh citypulse-airflow --zone=us-central1-a
# 4 GB swap: the e2-micro has 1 GB of RAM
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
python3 -m venv ~/airflow-env && source ~/airflow-env/bin/activate
pip install "apache-airflow==2.8.1" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"
pip install -r ingestion/requirements.txt -r processing/requirements.txt -r loading/requirements.txt
pip install dbt-bigquery==1.7.0 google-cloud-bigquery==3.13.0
```

Airflow ran as `airflow standalone` under a `systemd` unit (`Restart=always`,
`AIRFLOW__CORE__LOAD_EXAMPLES=False`, `GCP_BUCKET_NAME` in the environment). The repository was
cloned on the VM with a deploy key, and DAG files were copied to `~/airflow/dags/prod/`; every
extract task then ran `git pull` on that clone (audit H5).

Airflow Variables: `citypulse_repo_path`, `citypulse_bucket`, `citypulse_project_id`.
dbt profile on the VM (`~/.dbt/profiles.yml`, never committed): BigQuery, `method: oauth` (the
VM's service account), `dataset: citypulse_marts`, `location: us-central1`.

The UI was reached only through a tunnel:

```bash
gcloud compute ssh citypulse-airflow --zone=us-central1-a -- -L 8080:localhost:8080 -N
```

## 7. Schedules

| DAG | Schedule | Does |
|---|---|---|
| `prod.daily_ingestion` | `0 6 * * *` | Weather and air quality for the run's logical date, in parallel → `dbt run` |
| `prod.monthly_ingestion` | `0 6 8 * *` | Citi Bike for the month two months back → `dbt run` |

## 8. Running pieces by hand

Every layer has a runner per source, each with `--dry-run`:

```bash
python -m ingestion.run_weather     --date 2026-01-15
python -m processing.run_weather    --date 2026-01-15
python -m loading.run_weather       --date 2026-01-15
python -m ingestion.run_citibike    --year 2026 --month 1     # same for processing/loading
cd transformation && dbt build
```

`backfill.py` replays extract → process → load for weather and air quality over the months
listed in `MONTHS_TO_BACKFILL` inside the file.

## 9. CI/CD

`.github/workflows/deploy.yml`, on pull requests to and pushes on `main`:

- path filter → `transformation/` changes run `dbt compile` + `dbt test` and comment the result;
  `infrastructure/terraform/` changes run `fmt -check`, `validate`, `plan` (commented on the PR);
- on push to `main`, `terraform apply -auto-approve`.

dbt in CI runs against the production datasets (audit H2).
