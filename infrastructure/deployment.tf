resource "aws_ecs_task_definition" "deployments" {
  family                   = "ml-workflow-deployments"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.deployment_role.arn

  container_definitions = jsonencode([
    {
      name  = "deployments"
      image = "${var.deployments_image}:latest"
      environment = [
        {
          name  = "MLFLOW_TRACKING_URI"
          value = "http://mlflow.${aws_route53_zone.private.name}:5000"
        },
        {
          name  = "PREFECT_API_URL"
          value = "http://prefect.${aws_route53_zone.private.name}:4200/api"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-workflow"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "deployments"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "deployments" {
  name            = "ml-workflow-deployments"
  cluster         = aws_ecs_cluster.ml_workflow.id
  task_definition = aws_ecs_task_definition.deployments.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}
