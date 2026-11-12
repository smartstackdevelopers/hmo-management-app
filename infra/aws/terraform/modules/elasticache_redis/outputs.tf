output "redis_primary_endpoint" {
  value = try(aws_elasticache_replication_group.main[0].primary_endpoint_address, null)
}
