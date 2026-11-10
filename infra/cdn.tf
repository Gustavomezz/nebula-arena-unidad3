resource "google_storage_bucket" "stream" {
  count                       = var.crear_cdn ? 1 : 0
  name                        = "${var.proyecto}-nebula-stream"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  soft_delete_policy { retention_duration_seconds = 0 }
  labels = local.labels
}

resource "google_storage_bucket_iam_member" "stream" {
  count  = var.crear_cdn ? 1 : 0
  bucket = google_storage_bucket.stream[0].name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_compute_backend_bucket" "stream" {
  count       = var.crear_cdn ? 1 : 0
  name        = "${local.nombre}-stream"
  bucket_name = google_storage_bucket.stream[0].name
  enable_cdn  = true
  cdn_policy {
    cache_mode  = "CACHE_ALL_STATIC"
    default_ttl = 3600
    max_ttl     = 86400
  }
}

resource "google_compute_url_map" "stream" {
  count           = var.crear_cdn ? 1 : 0
  name            = "${local.nombre}-cdn"
  default_service = google_compute_backend_bucket.stream[0].id
}

resource "google_compute_target_http_proxy" "stream" {
  count   = var.crear_cdn ? 1 : 0
  name    = "${local.nombre}-cdn"
  url_map = google_compute_url_map.stream[0].id
}

resource "google_compute_global_forwarding_rule" "stream" {
  count      = var.crear_cdn ? 1 : 0
  name       = "${local.nombre}-cdn"
  target     = google_compute_target_http_proxy.stream[0].id
  port_range = "80"
}
