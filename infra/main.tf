terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
  backend "gcs" {}
}

provider "google" {
  project = var.proyecto
  region  = var.region
  zone    = var.zona
}

locals {
  nombre = "nebula-${var.entorno}"
  labels = { proyecto = "nebula-arena", entorno = var.entorno, uso = "laboratorio" }
  apis = toset([
    "compute.googleapis.com", "container.googleapis.com", "artifactregistry.googleapis.com",
    "run.googleapis.com", "firestore.googleapis.com", "iam.googleapis.com",
    "iamcredentials.googleapis.com", "sts.googleapis.com", "cloudresourcemanager.googleapis.com",
    "cloudasset.googleapis.com"
  ])
}

resource "google_project_service" "apis" {
  for_each           = local.apis
  service            = each.value
  disable_on_destroy = false
}
