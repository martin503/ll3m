resource "aws_route53_zone" "private" {
  name = "ml-workflow.internal"

  vpc {
    vpc_id = module.vpc.vpc_id
  }
}

resource "aws_route53_record" "mlflow" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "mlflow.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "prefect" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "prefect.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "prometheus" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "prometheus.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "grafana" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "grafana.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "api.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.private.zone_id
  name    = "app.${aws_route53_zone.private.name}"
  type    = "A"

  alias {
    name                   = aws_lb.ml_workflow.dns_name
    zone_id                = aws_lb.ml_workflow.zone_id
    evaluate_target_health = true
  }
}
