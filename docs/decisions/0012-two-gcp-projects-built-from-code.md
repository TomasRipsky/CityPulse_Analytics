# 0012 — Two GCP projects built from code, least-privilege identities

- **Status:** Accepted
- **Date:** 2026-10-05
- **Refines:** [0005](0005-workload-identity-federation-for-ci.md)

## Context
Version 1 lived in one hand-configured project: a service account shared by the VM, CI and
Terraform, extra roles granted by hand (one of them, `projectIamAdmin`, let it make itself
owner), and a federation condition that admitted any branch and any workflow of the repository.
Its Terraform state lived inside the bucket it managed. None of it could be rebuilt from the repo.

## Decision
- Two projects in the organisation, **`citypulse-tr-dev`** (a sample of the data; CI builds every
  pull request there) and **`citypulse-tr-prod`** (the full dataset). Each is created by
  `make bootstrap` — project, billing link, a €5 budget with alerts at 50/90/100% — and everything
  inside it by Terraform (`infra/gcp/`, one workspace per environment, local state: only one
  person applies it).
- One service account, **`citypulse-pipeline`**: object admin on the lake bucket, data editor on
  the four datasets, BigQuery job user. Nothing on IAM. Every binding is in Terraform.
- People run the pipeline **as** that account (impersonation through
  `iam.serviceAccountTokenCreator`), never with their own broader rights and never with a key —
  the organisation forbids keys anyway.
- **Workload Identity Federation only in dev**, only for this repository's `citypulse-*`
  workflows, never for `pull_request_target`. Nothing in CI touches prod, so prod trusts no one
  outside.
- A daily BigQuery query quota (100 GiB) stops runaway scans, which a budget alert only reports.

## Alternatives considered
- One project with CI datasets — cheaper to set up, but pull-request code could read and write
  the real data.
- Remote state in a bucket — needed when several people or machines apply; not here.
- Federation in prod for a scheduled pipeline — the dataset is frozen; nothing runs on a schedule.

## Consequences
- `make destroy` / `make apply` rebuild an environment from nothing (tested on dev).
- The local state file must not be lost; losing it means importing or re-creating resources.
- Right after the IAM API is enabled, creating a federation pool fails with 403 for a minute or
  two; Terraform waits 90 seconds before creating it.
