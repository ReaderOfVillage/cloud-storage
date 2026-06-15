terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
  }
}

resource "digitalocean_container_registry" "main" {
  name                   = "cloud-storage"
  subscription_tier_slug = "starter"    # free tier
}

# allow kubernetes to pull from registry
resource "digitalocean_container_registry_docker_credentials" "main" {
  registry_name = digitalocean_container_registry.main.name
}