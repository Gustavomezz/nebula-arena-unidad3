resource "google_compute_network" "vpc" {
  name                    = "${local.nombre}-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "juego" {
  name                     = "${local.nombre}-subred"
  ip_cidr_range            = "10.40.0.0/20"
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.44.0.0/16"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.45.0.0/20"
  }
}

resource "google_compute_firewall" "juego" {
  name          = "${local.nombre}-partidas"
  network       = google_compute_network.vpc.name
  target_tags   = ["nebula-game"]
  source_ranges = concat([google_compute_subnetwork.juego.ip_cidr_range], var.acceso_adicional_juego)
  allow {
    protocol = "tcp"
    ports    = ["7000-8000"]
  }
}

resource "google_compute_firewall" "ssh_iap" {
  name          = "${local.nombre}-ssh-iap"
  network       = google_compute_network.vpc.name
  target_tags   = ["nebula-loadgen"]
  source_ranges = ["35.235.240.0/20"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
