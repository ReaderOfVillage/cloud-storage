variable "do_token" {
  type      = string
  sensitive = true
}

variable "region" {
  type    = string
  default = "ams3" 
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "spaces_key" {
  type      = string
  sensitive = true
}

variable "spaces_secret" {
  type      = string
  sensitive = true
}

variable "node_count" {
  type    = number
  default = 1
}

variable "node_size" {
  type    = string
  default = "s-2vcpu-2gb"
}