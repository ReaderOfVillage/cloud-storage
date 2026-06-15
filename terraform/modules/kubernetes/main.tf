terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
  }
}

resource "digitalocean_kubernetes_cluster" "main" {
  name    = "cloud-storage-${var.environment}"
  region  = var.region
  version = "1.36.0-do.1"
  ha      = false

  node_pool {
    name       = "default"
    size       = var.node_size   
    node_count = var.node_count
  }
}