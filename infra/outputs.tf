output "cluster" { value = google_container_cluster.nebula.name }
output "registro" { value = "${var.region}-docker.pkg.dev/${var.proyecto}/nebula" }
output "generador" { value = try(google_compute_instance.generador[0].name, null) }
output "stream_url" { value = try("http://${google_compute_global_forwarding_rule.stream[0].ip_address}", null) }
output "stream_bucket" { value = try(google_storage_bucket.stream[0].name, null) }
output "leaderboard_url" { value = try(google_cloud_run_v2_service.scores[0].uri, null) }
