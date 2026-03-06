# -----------------------------------------------------------------------------
# Firewall — acceso restringido a la VM
#
# Abrimos únicamente dos puertos y solo desde tu IP personal:
# - 22   (SSH): para conectarte a la VM y administrarla
# - 8080 (Airflow UI): para ver los DAGs desde el navegador
#
# Restringir por IP es más seguro que abrir al mundo (0.0.0.0/0).
# Si tu IP cambia, actualiza la variable my_ip y aplica terraform apply.
# -----------------------------------------------------------------------------

resource "google_compute_firewall" "airflow_access" {
  name    = "citypulse-airflow-access"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22", "8080"]
  }

  # Solo accesible desde tu IP personal
  source_ranges = ["${var.my_ip}/32"]

  # Aplica únicamente a VMs con el tag "airflow-server"
  target_tags = ["airflow-server"]
}
