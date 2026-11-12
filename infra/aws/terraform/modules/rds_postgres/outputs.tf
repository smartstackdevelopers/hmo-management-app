output "db_endpoint" {
  value = try(aws_db_instance.main[0].endpoint, null)
}

output "db_arn" {
  value = try(aws_db_instance.main[0].arn, null)
}
