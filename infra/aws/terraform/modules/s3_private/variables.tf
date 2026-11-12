variable "stack_enabled" {
  type    = bool
  default = false
}

variable "name_prefix" {
  type = string
}

variable "bucket_suffix" {
  type        = string
  description = "Unique suffix; never use tenant PII."
}
