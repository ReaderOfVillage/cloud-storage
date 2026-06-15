output "registry_name" {
  value = digitalocean_container_registry.main.name
}

output "endpoint" {
  value = digitalocean_container_registry.main.endpoint
}