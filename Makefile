.PHONY: help setup test lint fmt ingest

# Local settings (never committed): copy .env.example to .env. Make exports every variable in it.
-include .env
export

# Lake root: a local folder by default; set CITYPULSE_LAKE_URI=gs://<bucket> to use GCS.
CITYPULSE_LAKE_URI ?= .lake

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

ingest: ## Land data in the lake. Usage: make ingest ARGS="trips --from 2025-01"
	uv run citypulse ingest $(ARGS)
