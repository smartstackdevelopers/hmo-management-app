locals {
  enabled = var.stack_enabled ? 1 : 0
  services = ["api", "web", "ai", "worker"]
}

resource "aws_cloudwatch_log_group" "services" {
  for_each          = var.stack_enabled ? toset(local.services) : toset([])
  name              = "/hmore/${var.name_prefix}/${each.key}"
  retention_in_days = 30
  tags              = { Service = each.key }
}
