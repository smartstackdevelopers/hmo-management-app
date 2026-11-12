output "vpc_id" {
  value       = try(aws_vpc.main[0].id, null)
  description = "VPC id when stack_enabled."
}

output "public_subnet_ids" {
  value = try(aws_subnet.public[*].id, [])
}

output "private_app_subnet_ids" {
  value = try(aws_subnet.private_app[*].id, [])
}

output "private_db_subnet_ids" {
  value = try(aws_subnet.private_db[*].id, [])
}

output "security_group_ids" {
  value = {
    alb  = try(aws_security_group.alb[0].id, null)
    app  = try(aws_security_group.app[0].id, null)
    data = try(aws_security_group.data[0].id, null)
  }
}
