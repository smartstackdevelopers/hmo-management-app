output "region" {
  value       = var.aws_region
  description = "Selected AWS region."
}

output "stack_enabled" {
  value = var.stack_enabled
}

output "vpc_id" {
  value = module.networking.vpc_id
}

output "private_file_bucket" {
  value = module.s3_files.bucket_name
}

output "rds_endpoint" {
  value = try(module.rds[0].db_endpoint, null)
}

output "redis_endpoint" {
  value = try(module.redis[0].redis_primary_endpoint, null)
}

output "log_groups" {
  value = module.observability.log_group_names
}

output "provisioning_note" {
  value = var.stack_enabled ? "LIVE RESOURCES ENABLED — apply only with change approval" : "PREPARED ONLY — set stack_enabled=true after client approval"
}
