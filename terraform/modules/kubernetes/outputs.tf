output "cluster_id" {
  value = digitalocean_kubernetes_cluster.main.id
}

output "kube_config" {
  value     = digitalocean_kubernetes_cluster.main.kube_config[0].raw_config
  sensitive = true
}