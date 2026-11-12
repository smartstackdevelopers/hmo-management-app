variable "stack_enabled" {
  type        = bool
  description = "When false, no AWS resources are created (F7.6 safe default)."
  default     = false
}

variable "name_prefix" {
  type        = string
  description = "Resource name prefix."
}

variable "aws_region" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "create_nat_gateway" {
  type        = bool
  description = "NAT Gateway incurs hourly cost — PENDING APPROVAL before true in production."
  default     = false
}
