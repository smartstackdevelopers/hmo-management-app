locals {
  enabled    = var.stack_enabled ? 1 : 0
  bucket_name = "${var.name_prefix}-files-${var.bucket_suffix}"
}

resource "aws_s3_bucket" "files" {
  count  = local.enabled
  bucket = local.bucket_name
  tags = {
    Name    = local.bucket_name
    Purpose = "hmore-private-files"
  }
}

resource "aws_s3_bucket_public_access_block" "files" {
  count                   = local.enabled
  bucket                  = aws_s3_bucket.files[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "files" {
  count  = local.enabled
  bucket = aws_s3_bucket.files[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "files" {
  count  = local.enabled
  bucket = aws_s3_bucket.files[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "files" {
  count  = local.enabled
  bucket = aws_s3_bucket.files[0].id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
