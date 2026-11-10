resource "google_firestore_database" "scores" {
  project         = var.proyecto
  name            = "(default)"
  location_id     = var.region
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"
  depends_on      = [google_project_service.apis]
}

resource "google_service_account" "leaderboard" {
  account_id = "${local.nombre}-scores"
  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "scores" {
  project = var.proyecto
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.leaderboard.email}"
}

resource "google_cloud_run_v2_service" "scores" {
  count               = var.crear_serverless ? 1 : 0
  name                = "${local.nombre}-leaderboard"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels              = local.labels
  template {
    service_account                  = google_service_account.leaderboard.email
    max_instance_request_concurrency = 40
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.imagen_serverless
      resources {
        limits            = { cpu = "1", memory = "512Mi" }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      ports { container_port = 8080 }
    }
  }
  depends_on = [google_project_iam_member.scores, google_firestore_database.scores]
  lifecycle {
    precondition {
      condition     = !var.crear_serverless || length(var.imagen_serverless) > 0
      error_message = "Publica primero la imagen de la tabla de líderes."
    }
    # CI/CD administra las revisiones posteriores de la imagen.
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
}

resource "google_cloud_run_v2_service_iam_member" "publico" {
  count    = var.crear_serverless ? 1 : 0
  location = google_cloud_run_v2_service.scores[0].location
  name     = google_cloud_run_v2_service.scores[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
