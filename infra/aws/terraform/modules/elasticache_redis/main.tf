locals {
  enabled = var.stack_enabled ? 1 : 0
}

resource "aws_elasticache_subnet_group" "main" {
  count      = local.enabled
  name       = "${var.name_prefix}-redis"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_replication_group" "main" {
  count                      = local.enabled
  replication_group_id       = "${var.name_prefix}-redis"
  description                = "HMore Celery broker/cache"
  node_type                  = var.node_type
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.main[0].name
  security_group_ids         = var.security_group_ids
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = false
  tags                       = { Name = "${var.name_prefix}-redis" }
}
