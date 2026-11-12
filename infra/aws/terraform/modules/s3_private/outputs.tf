output "bucket_name" {
  value = try(aws_s3_bucket.files[0].id, null)
}

output "bucket_arn" {
  value = try(aws_s3_bucket.files[0].arn, null)
}
