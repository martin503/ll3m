resource "aws_secretsmanager_secret" "db_credentials" {
  name = "ml-workflow-db-credentials"
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}

resource "aws_secretsmanager_secret" "grafana_credentials" {
  name = "ml-workflow-grafana-credentials"
}

resource "aws_secretsmanager_secret_version" "grafana_credentials" {
  secret_id = aws_secretsmanager_secret.grafana_credentials.id
  secret_string = jsonencode({
    username = var.grafana_admin_user
    password = var.grafana_admin_password
  })
}
