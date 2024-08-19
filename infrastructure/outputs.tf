output "alb_dns_name" {
  description = "The DNS name of the Application Load Balancer"
  value       = aws_lb.ml_workflow.dns_name
}

output "mlflow_url" {
  description = "The URL for the MLflow service"
  value       = "http://${aws_lb.ml_workflow.dns_name}/mlflow"
}

output "prefect_url" {
  description = "The URL for the Prefect service"
  value       = "http://${aws_lb.ml_workflow.dns_name}/api"
}

output "grafana_url" {
  description = "The URL for the Grafana service"
  value       = "http://${aws_lb.ml_workflow.dns_name}/grafana"
}

output "app_url" {
  description = "The URL for the main application"
  value       = "http://${aws_lb.ml_workflow.dns_name}"
}

output "prefect_db_endpoint" {
  value       = aws_db_instance.prefect.endpoint
  description = "The connection endpoint for the Prefect RDS instance"
}

output "mlflow_db_endpoint" {
  value       = aws_db_instance.mlflow.endpoint
  description = "The connection endpoint for the MLflow RDS instance"
}
