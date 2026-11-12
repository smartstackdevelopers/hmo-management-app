variable "stack_enabled" {
  type    = bool
  default = false
}

variable "name_prefix" {
  type = string
}

variable "db_subnet_ids" {
  type = list(string)
}

variable "vpc_security_group_ids" {
  type = list(string)
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage_gb" {
  type    = number
  default = 50
}
