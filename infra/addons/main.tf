terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
    helm   = { source = "hashicorp/helm", version = "~> 3.0" }
  }
  backend "gcs" {}
}
variable "proyecto" { type = string }
variable "cluster" { default = "nebula-dev" }
variable "zona" { default = "us-central1-a" }
provider "google" { project = var.proyecto }
data "google_container_cluster" "nebula" {
  name     = var.cluster
  location = var.zona
}
data "google_client_config" "actual" {}
provider "helm" {
  kubernetes = {
    host                   = "https://${data.google_container_cluster.nebula.endpoint}"
    token                  = data.google_client_config.actual.access_token
    cluster_ca_certificate = base64decode(data.google_container_cluster.nebula.master_auth[0].cluster_ca_certificate)
  }
}
resource "helm_release" "monitoreo" {
  name             = "monitoreo"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "72.6.2"
  namespace        = "monitoring"
  create_namespace = true
  timeout          = 900
  values           = [file("${path.module}/../../k8s/monitoreo-values.yaml")]
}
resource "helm_release" "agones" {
  name             = "agones"
  repository       = "https://agones.dev/chart/stable"
  chart            = "agones"
  version          = "1.62.0"
  namespace        = "agones-system"
  create_namespace = true
  timeout          = 900
  values = [yamlencode({
    agones = {
      metrics   = { serviceMonitor = { enabled = true } }
      allocator = { service = { serviceType = "ClusterIP" } }
    }
  })]
  depends_on = [helm_release.monitoreo]
}
