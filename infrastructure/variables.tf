variable "aws_region" {
  description = "The AWS region to deploy resources"
  default     = "us-east-1"
}

variable "db_username" {
  description = "Username for the RDS instance"
  sensitive   = true
}

variable "db_password" {
  description = "Password for the RDS instance"
  sensitive   = true
}

variable "grafana_admin_user" {
  description = "Grafana admin username"
  sensitive   = true
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  sensitive   = true
}

variable "api_image" {
  description = "Docker image for the API service"
  type        = string
}

variable "app_image" {
  description = "Docker image for the main application"
  type        = string
}

variable "mlflow_image" {
  description = "Docker image for MLflow"
  type        = string
}

variable "deployments_image" {
  description = "Docker image for deployments"
  type        = string
}
