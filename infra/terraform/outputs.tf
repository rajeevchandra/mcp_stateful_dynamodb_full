output "cluster_name" {
  value       = aws_ecs_cluster.this.name
  description = "ECS cluster name"
}

output "service_name" {
  value       = aws_ecs_service.this.name
  description = "ECS service name"
}

output "log_group" {
  value       = aws_cloudwatch_log_group.svc.name
  description = "CloudWatch Logs group"
}

output "dynamodb_table" {
  value       = aws_dynamodb_table.mcp_state.name
  description = "DynamoDB table used for state"
}

output "security_group_id" {
  value       = aws_security_group.svc.id
  description = "Security group that allows access to port 3333"
}

output "subnets" {
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  description = "Public subnets used by the service"
}
