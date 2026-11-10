terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}
variable "proyecto" { type = string }
provider "google" { project = var.proyecto }
resource "google_storage_bucket" "estado" {
  name                        = "${var.proyecto}-nebula-tfstate"
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  force_destroy               = true
  versioning { enabled = true }
}
output "bucket" { value = google_storage_bucket.estado.name }
