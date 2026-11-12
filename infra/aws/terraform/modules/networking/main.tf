locals {
  enabled    = var.stack_enabled ? 1 : 0
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
  public     = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  private    = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 2)]
  database   = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 4)]
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  count                = local.enabled
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.name_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  count  = local.enabled
  vpc_id = aws_vpc.main[0].id
  tags   = { Name = "${var.name_prefix}-igw" }
}

resource "aws_subnet" "public" {
  count                   = local.enabled * length(local.azs)
  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = local.public[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.name_prefix}-public-${count.index + 1}"
    Tier = "public"
  }
}

resource "aws_subnet" "private_app" {
  count             = local.enabled * length(local.azs)
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = local.private[count.index]
  availability_zone = local.azs[count.index]
  tags = {
    Name = "${var.name_prefix}-private-app-${count.index + 1}"
    Tier = "private-app"
  }
}

resource "aws_subnet" "private_db" {
  count             = local.enabled * length(local.azs)
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = local.database[count.index]
  availability_zone = local.azs[count.index]
  tags = {
    Name = "${var.name_prefix}-private-db-${count.index + 1}"
    Tier = "private-db"
  }
}

resource "aws_eip" "nat" {
  count  = local.enabled * (var.create_nat_gateway ? 1 : 0)
  domain = "vpc"
  tags   = { Name = "${var.name_prefix}-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  count         = local.enabled * (var.create_nat_gateway ? 1 : 0)
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${var.name_prefix}-nat" }
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  count  = local.enabled
  vpc_id = aws_vpc.main[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }
  tags = { Name = "${var.name_prefix}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = local.enabled * length(local.azs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table" "private_app" {
  count  = local.enabled
  vpc_id = aws_vpc.main[0].id
  dynamic "route" {
    for_each = var.create_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[0].id
    }
  }
  tags = { Name = "${var.name_prefix}-private-app-rt" }
}

resource "aws_route_table_association" "private_app" {
  count          = local.enabled * length(local.azs)
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private_app[0].id
}

resource "aws_route_table" "private_db" {
  count  = local.enabled
  vpc_id = aws_vpc.main[0].id
  tags   = { Name = "${var.name_prefix}-private-db-rt" }
}

resource "aws_route_table_association" "private_db" {
  count          = local.enabled * length(local.azs)
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private_db[0].id
}

# --- Security groups (least-privilege baseline) ---

resource "aws_security_group" "alb" {
  count       = local.enabled
  name        = "${var.name_prefix}-alb"
  description = "HTTPS ingress to load balancer"
  vpc_id      = aws_vpc.main[0].id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Public HTTPS"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.name_prefix}-sg-alb" }
}

resource "aws_security_group" "app" {
  count       = local.enabled
  name        = "${var.name_prefix}-app"
  description = "ECS tasks — API, web, AI, workers"
  vpc_id      = aws_vpc.main[0].id
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
    description     = "From ALB"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Egress to Auth0, LLM APIs, etc."
  }
  tags = { Name = "${var.name_prefix}-sg-app" }
}

resource "aws_security_group" "data" {
  count       = local.enabled
  name        = "${var.name_prefix}-data"
  description = "RDS and Redis — private only"
  vpc_id      = aws_vpc.main[0].id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
    description     = "Postgres from app tier"
  }
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
    description     = "Redis from app tier"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.name_prefix}-sg-data" }
}
