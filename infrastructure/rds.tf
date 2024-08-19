resource "aws_db_instance" "prefect" {
  identifier        = "ml-workflow-prefect-db"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  db_name           = "prefect"
  username          = jsondecode(aws_secretsmanager_secret_version.db_credentials.secret_string)["username"]
  password          = jsondecode(aws_secretsmanager_secret_version.db_credentials.secret_string)["password"]

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  skip_final_snapshot = true
}

resource "aws_db_instance" "mlflow" {
  identifier        = "ml-workflow-mlflow-db"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  db_name           = "mlflow"
  username          = jsondecode(aws_secretsmanager_secret_version.db_credentials.secret_string)["username"]
  password          = jsondecode(aws_secretsmanager_secret_version.db_credentials.secret_string)["password"]

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  skip_final_snapshot = true
}

resource "aws_db_subnet_group" "rds" {
  name       = "ml-workflow-rds-subnet-group"
  subnet_ids = module.vpc.private_subnets
}
