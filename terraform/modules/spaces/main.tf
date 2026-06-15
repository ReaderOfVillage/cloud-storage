terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
  }
}

resource "digitalocean_spaces_bucket" "main" {
  name   = "cloud-storage-${var.environment}"
  region = var.region
}