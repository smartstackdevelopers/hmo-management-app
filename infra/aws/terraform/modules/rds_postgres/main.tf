locals {
  enabled = var.stack_enabled ? 1 : 0
}

resource "aws_db_subnet_group" "main" {
  count      = local.enabled
  name       = "${var.name_prefix}-db"
  subnet_ids = var.db_subnet_ids
  tags       = { Name = "${var.name_prefix}-db-subnet-group" }
}

resource "aws_db_instance" "main" {
  count                  = local.enabled
  identifier             = "${var.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage_gb
  storage_encrypted      = true
  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = var.vpc_security_group_ids
  publicly_accessible    = false
  backup_retention_period = 7
  deletion_protection    = true
  skip_final_snapshot    = true
  username               = "hmore_admin"
  manage_master_user_password = true
  tags = { Name = "${var.name_prefix}-rds" }
}
