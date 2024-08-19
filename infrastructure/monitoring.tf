resource "aws_ecs_task_definition" "prometheus" {
  family                   = "ml-workflow-prometheus"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "prometheus"
      image = "prom/prometheus:latest"
      portMappings = [
        {
          containerPort = 9090
          hostPort      = 9090
        }
      ]
      environment = [
        {
          name  = "PROMETHEUS_CONFIG"
          value = base64encode(file("${path.module}/../monitoring/prometheus.yml"))
        }
      ]
      command = [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--web.console.libraries=/usr/share/prometheus/console_libraries",
        "--web.console.templates=/usr/share/prometheus/consoles"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-workflow"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "prometheus"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "prometheus" {
  name            = "ml-workflow-prometheus"
  cluster         = aws_ecs_cluster.ml_workflow.id
  task_definition = aws_ecs_task_definition.prometheus.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

resource "aws_ecs_task_definition" "pushgateway" {
  family                   = "ml-workflow-pushgateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "pushgateway"
      image = "prom/pushgateway"
      portMappings = [
        {
          containerPort = 9091
          hostPort      = 9091
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-workflow"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "pushgateway"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "pushgateway" {
  name            = "ml-workflow-pushgateway"
  cluster         = aws_ecs_cluster.ml_workflow.id
  task_definition = aws_ecs_task_definition.pushgateway.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

resource "aws_ecs_task_definition" "grafana" {
  family                   = "ml-workflow-grafana"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "grafana"
      image = "grafana/grafana:latest"
      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
        }
      ]
      environment = [
        {
          name  = "GF_INSTALL_PLUGINS"
          value = "grafana-clock-panel,grafana-simple-json-datasource"
        },
        {
          name  = "GF_SECURITY_ADMIN_USER"
          value = jsondecode(aws_secretsmanager_secret_version.grafana_credentials.secret_string)["username"]
        },
        {
          name  = "GF_SECURITY_ADMIN_PASSWORD"
          value = jsondecode(aws_secretsmanager_secret_version.grafana_credentials.secret_string)["password"]
        },
        {
          name  = "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH"
          value = "/etc/grafana/provisioning/dashboards/dashboard.json"
        },
        {
          name  = "GF_DATASOURCES_PROMETHEUS_URL"
          value = "http://prometheus.${aws_route53_zone.private.name}:9090"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-workflow"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "grafana"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "grafana" {
  name            = "ml-workflow-grafana"
  cluster         = aws_ecs_cluster.ml_workflow.id
  task_definition = aws_ecs_task_definition.grafana.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana.arn
    container_name   = "grafana"
    container_port   = 3000
  }
}

resource "aws_lb_target_group" "grafana" {
  name        = "ml-workflow-grafana-tg"
  port        = 3000
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

resource "aws_lb_listener_rule" "grafana" {
  listener_arn = aws_lb_listener.front_end.arn
  priority     = 130

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }

  condition {
    path_pattern {
      values = ["/grafana/*"]
    }
  }
}
