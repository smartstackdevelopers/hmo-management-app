terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "HMore"
      Environment = "production"
      ManagedBy   = "terraform"
      Compliance  = "uk-eu-data-residency-pending-approval"
    }
  }
}

module "networking" {
  source             = "../../modules/networking"
  stack_enabled      = var.stack_enabled
  name_prefix        = var.name_prefix
  aws_region         = var.aws_region
  create_nat_gateway = var.create_nat_gateway
}

module "s3_files" {
  source         = "../../modules/s3_private"
  stack_enabled  = var.stack_enabled
  name_prefix    = var.name_prefix
  bucket_suffix  = var.s3_bucket_suffix
}

module "rds" {
  count  = var.stack_enabled ? 1 : 0
  source = "../../modules/rds_postgres"

  stack_enabled          = true
  name_prefix            = var.name_prefix
  db_subnet_ids          = module.networking.private_db_subnet_ids
  vpc_security_group_ids = compact([module.networking.security_group_ids.data])
}

module "redis" {
  count  = var.stack_enabled ? 1 : 0
  source = "../../modules/elasticache_redis"

  stack_enabled      = true
  name_prefix        = var.name_prefix
  subnet_ids         = module.networking.private_db_subnet_ids
  security_group_ids = compact([module.networking.security_group_ids.data])
}

module "observability" {
  source        = "../../modules/observability"
  stack_enabled = var.stack_enabled
  name_prefix   = var.name_prefix
}
