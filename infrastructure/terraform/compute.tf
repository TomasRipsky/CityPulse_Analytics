# -----------------------------------------------------------------------------
# Compute Engine — VM para Airflow
# Usamos e2-micro que está en el free tier permanente de GCP.
# 1 vCPU, 1GB RAM — suficiente para Airflow standalone con SQLite
# y el volumen de DAGs de este proyecto.
# -----------------------------------------------------------------------------

resource "google_compute_instance" "airflow" {
  name         = "citypulse-airflow"
  machine_type = "e2-micro"
  zone         = "${var.region}-a"

  tags = ["airflow-server"]

  boot_disk {
    initialize_params {
      # Ubuntu 22.04 LTS — estable, bien documentado y compatible con Airflow
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30 # GB — máximo gratuito en el free tier
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"

    # IP externa efímera — gratuita en e2-micro dentro de us-central1
    access_config {}
  }

  # Asociamos la service account del proyecto para que los DAGs
  # puedan acceder a GCS y BigQuery sin credenciales adicionales.
  service_account {
    email  = google_service_account.citypulse_sa.email
    scopes = ["cloud-platform"]
  }

  # Script de arranque — se ejecuta una única vez al crear la VM.
  # Instala Python, pip y las dependencias base del sistema.
  # Airflow se instalará manualmente en el paso siguiente.
  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update -y
    apt-get install -y python3-pip python3-venv git
    pip3 install --upgrade pip
  EOT

  labels = {
    project     = "citypulse"
    environment = var.environment
    role        = "airflow"
  }
}

# IP externa de la VM — la necesitamos para conectarnos por SSH
# y para acceder a la UI de Airflow desde el navegador.
output "airflow_vm_ip" {
  description = "IP pública de la VM de Airflow"
  value       = google_compute_instance.airflow.network_interface[0].access_config[0].nat_ip
}
