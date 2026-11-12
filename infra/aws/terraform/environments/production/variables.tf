variable "aws_region" {
  type        = string
  description = "Primary AWS region. Default eu-west-2 (London) — PENDING client approval."
  default     = "eu-west-2"
}

variable "name_prefix" {
  type        = string
  description = "Short name prefix for resources."
  default     = "hmore-prod"
}

variable "stack_enabled" {
  type        = bool
  description = "When false, Terraform defines modules but creates zero AWS resources."
  default     = false
}

variable "create_nat_gateway" {
  type        = bool
  description = "NAT Gateway cost — enable only after approval."
  default     = false
}

variable "s3_bucket_suffix" {
  type        = string
  description = "Globally unique bucket suffix (account id or random)."
  default     = "pending-approval"
}
