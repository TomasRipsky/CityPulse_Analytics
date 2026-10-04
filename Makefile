.PHONY: help setup test lint fmt ingest load bootstrap init plan apply destroy gh-vars

# Local settings (never committed): copy .env.example to .env. Make exports every variable in it.
-include .env
export

ENV ?= dev
PROJECT_PREFIX ?= citypulse-tr
PROJECT_ID := $(PROJECT_PREFIX)-$(ENV)
# Budget alert amount, in the billing account's currency (EUR for this account).
BUDGET_AMOUNT ?= 5
TF := terraform -chdir=infra/gcp

ifeq ($(filter $(ENV),dev prod),)
$(error ENV must be dev or prod, got '$(ENV)')
endif

# Lake root: the local folder .lake by default; LAKE=gcs uses the ENV project's bucket.
ifeq ($(LAKE),gcs)
CITYPULSE_LAKE_URI := gs://$(PROJECT_ID)-lake
endif
CITYPULSE_LAKE_URI ?= .lake
CITYPULSE_BQ_PROJECT ?= $(PROJECT_ID)

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

TF_VARS = -var env=$(ENV) -var project_id=$(PROJECT_ID) -var operator="user:$$(gcloud config get account 2>/dev/null)"

plan: init ## Show infrastructure changes for ENV
	$(TF) plan $(TF_VARS)

apply: init ## Create/update ENV's infrastructure (expected cost: ~€0/month dev, cents prod)
	$(TF) apply $(TF_VARS)

destroy: init ## Delete everything Terraform created in ENV — lake and tables included
	$(TF) destroy $(TF_VARS)

gh-vars: init ## Publish dev's project, WIF provider and service account to the GitHub environment dev
	@test "$(ENV)" = dev || { echo "only dev has CI federation"; exit 1; }
	gh variable set CITYPULSE_PROJECT --env dev --body "$(PROJECT_ID)"
	gh variable set CITYPULSE_WIF_PROVIDER --env dev --body "$$($(TF) output -raw workload_identity_provider)"
	gh variable set CITYPULSE_SERVICE_ACCOUNT --env dev --body "$$($(TF) output -raw pipeline_service_account)"
