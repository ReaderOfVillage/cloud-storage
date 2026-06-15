terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    endpoints = {
      s3 = "https://ams3.digitaloceanspaces.com"
    }
    region                      = "us-east-1"
    bucket                      = "cloud-storage-tfstate"
    key                         = "prod/terraform.tfstate"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true    
  }
}

provider "digitalocean" {
  token = var.do_token
  spaces_access_id  = var.spaces_key
  spaces_secret_key = var.spaces_secret
}

module "kubernetes" {
  source      = "../../modules/kubernetes"
  environment = var.environment
  region      = var.region
  node_count  = var.node_count
  node_size   = var.node_size
}

# module "registry" {
#   source      = "../../modules/registry"
#   environment = var.environment
# }

module "spaces" {
  source      = "../../modules/spaces"
  environment = var.environment
  region      = var.region
}