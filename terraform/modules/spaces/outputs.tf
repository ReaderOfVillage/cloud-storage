output "bucket_name" {
  value = digitalocean_spaces_bucket.main.name
}

output "bucket_domain" {
  value = digitalocean_spaces_bucket.main.bucket_domain_name
}