terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.42.0"
    }
  }

  backend "s3" {
    region = "eu-central-1"
    bucket = "s3-shared-wallet-tfstate"
  }
}

provider "aws" {
  region = "eu-central-1"
}

locals {
  usernames = lower("${var.username1}-${var.username2}")
}

resource "aws_dynamodb_table" "table-sw-users" {
  name         = "table-sw-${local.usernames}-payments"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "wallet"
  range_key    = "timestamp"

  attribute {
    name = "wallet"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "terraform_aws_lambda_role_${local.usernames}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "iam_policy_for_lambda" {

  name        = "aws_iam_policy_for_terraform_aws_lambda_role_${local.usernames}"
  path        = "/"
  description = "AWS IAM Policy for managing aws lambda role"
  policy      = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    },
    {
      "Action" : [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:eu-central-1:*:table/table-sw-${local.usernames}*",
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn
}

resource "aws_lambda_function" "fn-shared-wallet" {
  filename         = "${path.module}/../my_deployment_package.zip"
  source_code_hash = filebase64sha256("${path.module}/../my_deployment_package.zip")
  function_name    = "fn-sw-${local.usernames}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.10"
  depends_on       = [aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role]

  environment {
    variables = {
      JSON_CONFIG = var.json_config
    }
  }
}

resource "aws_apigatewayv2_api" "api-gateway-sw" {
  name          = "api-sw-${local.usernames}"
  protocol_type = "HTTP"
  target        = aws_lambda_function.fn-shared-wallet.invoke_arn
}

resource "aws_apigatewayv2_integration" "example_lambda_integration" {
  api_id             = aws_apigatewayv2_api.api-gateway-sw.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.fn-shared-wallet.invoke_arn
}

resource "aws_lambda_permission" "permission-api-sw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn-shared-wallet.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.api-gateway-sw.execution_arn}/*/*"
}

output "api_gateway_url" {
  value = aws_apigatewayv2_api.api-gateway-sw.api_endpoint
}

