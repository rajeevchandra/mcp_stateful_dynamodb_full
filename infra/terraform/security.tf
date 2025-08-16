resource "aws_security_group" "svc" {
  name        = "${var.project_name}-sg"
  description = "Allow port 3333 from allowed CIDR"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "MCP HTTP"
    from_port   = 3333
    to_port     = 3333
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-sg" }
}
