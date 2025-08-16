variable "region" {
  type        = string
  description = "AWS region"
}

variable "project_name" {
  type        = string
  description = "A short name used to tag/name resources"
}

variable "container_image" {
  type        = string
  description = "ECR image URI (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/mcp-dynamodb:latest)"
}

variable "allowed_cidr" {
  type        = string
  description = "CIDR allowed to access port 3333 (e.g., 1.2.3.4/32)"
}

variable "fargate_cpu" {
  type    = number
  default = 256 # 0.25 vCPU
}

variable "fargate_memory" {
  type    = number
  default = 512 # 0.5 GB
}

variable "assign_public_ip" {
  type    = bool
  default = true
}
