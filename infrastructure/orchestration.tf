resource "aws_ecs_task_definition" "prefect" {
  family                   = "ml-workflow-prefect"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "prefect"
      image = "prefecthq/prefect:2.19.8-python3.9"
      portMappings = [
        {
          containerPort = 4200
          hostPort      = 4200
        }
      ]
      environment = [
        {
          name  = "PREFECT_UI_URL"
          value = "http://prefect.${aws_route53_zone.private.name}:4200"
        },
        {
          name  = "PREFECT_API_URL"
          value = "http://prefect.${aws_route53_zone.private.name}:4200/api"
        },
        {
          name  = "PREFECT_SERVER_API_HOST"
          value = "0.0.0.0"
        },
        {
          name  = "PREFECT_API_DATABASE_CONNECTION_URL"
          value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.prefect.endpoint}/${aws_db_instance.prefect.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-workflow"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "prefect"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "prefect" {
  name            = "ml-workflow-prefect"
  cluster         = aws_ecs_cluster.ml_workflow.id
  task_definition = aws_ecs_task_definition.prefect.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.prefect.arn
    container_name   = "prefect"
    container_port   = 4200
  }
}

resource "aws_lb_target_group" "prefect" {
  name        = "ml-workflow-prefect-tg"
  port        = 4200
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval            = 60
  }
}

resource "aws_lb_listener_rule" "prefect" {
  listener_arn = aws_lb_listener.front_end.arn
  priority     = 120

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prefect.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}
