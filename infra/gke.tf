resource "google_service_account" "nodos" {
  account_id   = "${local.nombre}-nodes"
  display_name = "Nodos de laboratorio Nebula Arena"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "nodos" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter", "roles/artifactregistry.reader"])
  project  = var.proyecto
  role     = each.value
  member   = "serviceAccount:${google_service_account.nodos.email}"
}

resource "google_container_cluster" "nebula" {
  name                     = local.nombre
  location                 = var.zona
  network                  = google_compute_network.vpc.id
  subnetwork               = google_compute_subnetwork.juego.id
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
  networking_mode          = "VPC_NATIVE"
  release_channel { channel = "REGULAR" }
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  workload_identity_config { workload_pool = "${var.proyecto}.svc.id.goog" }
  resource_labels = local.labels
  depends_on      = [google_project_service.apis]
}

resource "google_container_node_pool" "juego" {
  name               = "game-pool"
  cluster            = google_container_cluster.nebula.id
  location           = var.zona
  initial_node_count = var.nodos_iniciales
  autoscaling {
    min_node_count = var.nodos_minimos
    max_node_count = var.nodos_maximos
  }
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  node_config {
    machine_type    = var.maquina_nodos
    disk_size_gb    = 30
    disk_type       = "pd-standard"
    service_account = google_service_account.nodos.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    tags            = ["nebula-game"]
    labels          = { rol = "juego" }
    workload_metadata_config { mode = "GKE_METADATA" }
    metadata = { disable-legacy-endpoints = "true" }
  }
  depends_on = [google_project_iam_member.nodos]
}

resource "google_artifact_registry_repository" "imagenes" {
  location      = var.region
  repository_id = "nebula"
  format        = "DOCKER"
  labels        = local.labels
  depends_on    = [google_project_service.apis]
}

resource "google_compute_instance" "generador" {
  count        = var.crear_generador ? 1 : 0
  name         = "${local.nombre}-locust"
  zone         = var.zona
  machine_type = "e2-standard-8"
  labels       = local.labels
  tags         = ["nebula-loadgen"]
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 20
      type  = "pd-standard"
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.juego.id
    access_config {}
  }
  metadata                = { enable-oslogin = "TRUE" }
  metadata_startup_script = "#!/bin/bash\napt-get update\napt-get install -y python3-venv python3-pip git\n"
}
