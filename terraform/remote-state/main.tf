provider "aws" {
  region = "eu-central-1"
}

locals {
  usernames = lower("${var.username1}-${var.username2}")
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "s3b-tfstate-sw-${local.usernames}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "table-tfstate-sw-${local.usernames}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}