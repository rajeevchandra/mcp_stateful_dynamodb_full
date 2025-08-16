resource "aws_cloudwatch_log_group" "svc" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}
