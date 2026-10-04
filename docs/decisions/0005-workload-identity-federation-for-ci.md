# 0005 — Workload Identity Federation for GitHub Actions

- **Status:** Accepted
- **Date:** 2026-03-06 (recorded 2026-10-04)

## Context
CI must call GCP (dbt against BigQuery, Terraform). The repository is public, so a
long-lived service-account JSON key stored as a secret is a standing risk.

## Decision
GitHub Actions authenticates with **Workload Identity Federation**: a workload identity pool
trusts GitHub's OIDC tokens, an attribute condition admits only this repository, and the
workflow impersonates the `citypulse-sa` service account through
`google-github-actions/auth`. No key exists anywhere.

## Alternatives considered
- JSON key in a GitHub secret — simplest; rejected because a leaked key works until revoked.

## Consequences
- Short-lived tokens only; nothing to rotate or leak.
- Who may impersonate the account is decided by the attribute condition, so it must be
  as narrow as the use requires.

## Revisited 2026-10-04
The mechanism is right and stays. The condition admits any branch and any workflow of the
repository, and the account it unlocks holds `projectIamAdmin`, granted by hand — enough to
make itself owner (audit H4). Split CI and deploy identities and narrow the condition to `main`
for deploys.
