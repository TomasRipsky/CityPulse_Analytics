.PHONY: help setup test lint fmt ingest load transform airflow-build airflow-up airflow-down airflow-dags bootstrap operator-check init plan apply destroy gh-vars

# Local settings (never committed): copy .env.example to .env. Make exports every variable in it.
-include .env
export

ENV ?= dev
PROJECT_PREFIX ?= citypulse-tr
PROJECT_ID := $(PROJECT_PREFIX)-$(ENV)
# Budget alert amount, in the billing account's currency (EUR for this account).
BUDGET_AMOUNT ?= 5
# Terraform runs with the operator's own login (it manages IAM), even when ADC impersonates the
# pipeline account for everything else.
TF := GOOGLE_OAUTH_ACCESS_TOKEN=$$(gcloud auth print-access-token) terraform -chdir=infra/gcp

ifeq ($(filter $(ENV),dev prod),)
$(error ENV must be dev or prod, got '$(ENV)')
endif

# Lake root: the local folder .lake by default; LAKE=gcs uses the ENV project's bucket.
ifeq ($(LAKE),gcs)
CITYPULSE_LAKE_URI := gs://$(PROJECT_ID)-lake
endif
CITYPULSE_LAKE_URI ?= .lake
CITYPULSE_BQ_PROJECT ?= $(PROJECT_ID)
# Google client libraries read the project from here (otherwise they warn they cannot find one).
GOOGLE_CLOUD_PROJECT ?= $(PROJECT_ID)

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Create the virtualenv, install dependencies and the git hooks
	uv sync
	uv run --with pre-commit pre-commit install

test: ## Run the test suite
	uv run pytest

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

fmt: ## Auto-format and auto-fix
	uv run ruff format .
	uv run ruff check --fix .

ingest: ## Land data in the lake. Usage: make ingest ARGS="trips --from 2025-01" [LAKE=gcs ENV=dev]
	uv run citypulse ingest $(ARGS)

load: ## Load lake periods into ENV's BigQuery. Usage: make load ENV=dev ARGS="trips --from 2025-01"
	uv run citypulse load $(ARGS) --lake gs://$(PROJECT_ID)-lake --project $(PROJECT_ID)

transform/profiles.yml: transform/profiles.yml.example
	cp $< $@

transform: transform/profiles.yml ## Build and test the dbt models in ENV's BigQuery. Usage: make transform ENV=dev [ARGS="-s staging"]
	cd transform && uv run dbt deps --quiet && uv run dbt build --target $(ENV) --profiles-dir . $(ARGS)

GIT_REVISION := $(shell git rev-parse --short HEAD)$(shell git diff --quiet HEAD -- . ':!.internal' || echo -dirty)
# The frozen dataset: January 2025 to August 2026 (the last month Citi Bike had published).
CITYPULSE_LAST_DAY ?= 2026-08-31
COMPOSE := CITYPULSE_ENV=$(ENV) CITYPULSE_BQ_PROJECT=$(PROJECT_ID) CITYPULSE_LAKE_URI=gs://$(PROJECT_ID)-lake CITYPULSE_LAST_DAY=$(CITYPULSE_LAST_DAY) \
	docker compose -p citypulse-$(ENV) -f orchestration/docker-compose.yaml

airflow-build: ## Build the Airflow image for ENV from this commit (the deployed version)
	docker build -f orchestration/Dockerfile --build-arg GIT_REVISION=$(GIT_REVISION) -t citypulse-airflow:$(ENV) .

airflow-up: airflow-build ## Start Airflow for ENV on http://127.0.0.1:8080 (uses your gcloud ADC)
	$(COMPOSE) up -d --wait

airflow-down: ## Stop Airflow for ENV (keeps its metadata database)
	$(COMPOSE) down

airflow-dags: ## List the DAGs Airflow parsed, and any import errors
	$(COMPOSE) exec airflow-scheduler airflow dags list
	$(COMPOSE) exec airflow-scheduler airflow dags list-import-errors

bootstrap: ## One-off per ENV: create the project in the org, link billing, budget alert. BILLING_ACCOUNT=… ORG_ID=…
	@test -n "$(BILLING_ACCOUNT)" || { echo "set BILLING_ACCOUNT (see: gcloud billing accounts list)"; exit 1; }
	@test -n "$(ORG_ID)" || { echo "set ORG_ID (see: gcloud organizations list)"; exit 1; }
	gcloud projects create $(PROJECT_ID) --name="CityPulse $(ENV)" --organization=$(ORG_ID)
	gcloud billing projects link $(PROJECT_ID) --billing-account=$(BILLING_ACCOUNT)
	gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com billingbudgets.googleapis.com --project=$(PROJECT_ID)
	gcloud billing budgets create --billing-account=$(BILLING_ACCOUNT) --billing-project=$(PROJECT_ID) \
	  --display-name="citypulse-$(ENV)" --budget-amount=$(BUDGET_AMOUNT) --filter-projects=projects/$(PROJECT_ID) \
	  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0

init:
	$(TF) init -input=false
	$(TF) workspace select -or-create $(ENV)

OPERATOR_ACCOUNT := $(shell gcloud config get account 2>/dev/null)
TF_VARS = -var env=$(ENV) -var project_id=$(PROJECT_ID) -var operator="user:$(OPERATOR_ACCOUNT)"

operator-check:
	@test -n "$(OPERATOR_ACCOUNT)" || { echo "no active gcloud account: run gcloud auth login"; exit 1; }

plan: operator-check init ## Show infrastructure changes for ENV
	$(TF) plan $(TF_VARS)

apply: operator-check init ## Create/update ENV's infrastructure (expected cost: ~€0/month dev, cents prod)
	$(TF) apply $(TF_VARS)

destroy: operator-check init ## Delete everything Terraform created in ENV — lake and tables included
	$(TF) destroy $(TF_VARS)

gh-vars: init ## Publish dev's project, WIF provider and service account to the GitHub environment dev
	@test "$(ENV)" = dev || { echo "only dev has CI federation"; exit 1; }
	gh variable set CITYPULSE_PROJECT --env dev --body "$(PROJECT_ID)"
	gh variable set CITYPULSE_WIF_PROVIDER --env dev --body "$$($(TF) output -raw workload_identity_provider)"
	gh variable set CITYPULSE_SERVICE_ACCOUNT --env dev --body "$$($(TF) output -raw pipeline_service_account)"
