variable "proyecto" { type = string }
variable "region" { default = "us-central1" }
variable "zona" { default = "us-central1-a" }
variable "entorno" { default = "dev" }
variable "nodos_minimos" { default = 3 }
variable "nodos_maximos" { default = 16 }
variable "crear_generador" { default = true }
variable "crear_cdn" { default = false }
variable "crear_serverless" { default = false }
variable "imagen_serverless" { default = "" }
variable "github_repo" { default = "Gustavomezz/nebula-arena-unidad3" }
variable "acceso_adicional_juego" {
  description = "CIDR adicionales de clientes. La VM generadora ya tiene acceso por la subred."
  type        = list(string)
  default     = []
}
