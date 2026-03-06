terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Estado de Terraform almacenado en GCS para que sea compartido y persistente.
  # El bucket debe existir previamente (se crea una sola vez a mano o con el script de bootstrap).
  backend "gcs" {
    bucket = "city-pulse-tr"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
