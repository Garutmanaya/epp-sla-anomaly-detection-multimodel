##############################################
# Provider
##############################################

provider "aws" {
  region = var.region
}

##############################################
# Naming Convention (centralized)
##############################################

locals {
  project_name = "epp-sla-anomaly-detection-multimodel"

  # SageMaker
  model_name          = "${local.project_name}-model"
  endpoint_config     = "${local.project_name}-config"
  endpoint_name       = "${local.project_name}-endpoint"

  # Lambda
  lambda_name         = "${local.project_name}-relay"

  # API Gateway
  api_name            = "${local.project_name}-api"
}

##############################################
# 1. SageMaker Model
##############################################
# This defines the container (ECR image)
# No ModelDataUrl because model is inside container
##############################################

resource "aws_sagemaker_model" "model" {
  name               = local.model_name
  execution_role_arn = var.sagemaker_role_arn

  primary_container {
    image = var.ecr_image
  }
}

##############################################
# 2. Endpoint Configuration (SERVERLESS)
##############################################
# Defines compute characteristics
##############################################

resource "aws_sagemaker_endpoint_configuration" "config" {
  name = local.endpoint_config

  production_variants {
    variant_name = "AllTraffic"
    model_name   = aws_sagemaker_model.model.name

    # SERVERLESS CONFIG (core requirement)
    serverless_config {
      memory_size_in_mb = var.memory_size
      max_concurrency   = var.max_concurrency
    }
  }
}

##############################################
# 3. SageMaker Endpoint
##############################################
# Actual deployed HTTPS endpoint
##############################################

resource "aws_sagemaker_endpoint" "endpoint" {
  name                 = local.endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.config.name
}

##############################################
# 4. Lambda Packaging
##############################################
# Converts python file into deployable zip
##############################################

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/lambda_handler.py"
  output_path = "${path.module}/lambda.zip"
}

##############################################
# 5. Lambda Function (Relay)
##############################################
# This function:
# - receives API Gateway request
# - forwards to SageMaker endpoint
##############################################

resource "aws_lambda_function" "lambda" {
  function_name = local.lambda_name
  role          = var.lambda_role_arn

  handler = "lambda_handler.lambda_handler"
  runtime = "python3.11"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout      = 30
  memory_size  = 512

  environment {
    variables = {
      ENDPOINT_NAME = local.endpoint_name
    }
  }
}

##############################################
# 6. API Gateway (REST API)
##############################################
# Public entry point
##############################################

resource "aws_api_gateway_rest_api" "api" {
  name = local.api_name
}

##############################################
# Create /predict resource
##############################################

resource "aws_api_gateway_resource" "predict" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "predict"
}

##############################################
# POST method (no auth for simplicity)
##############################################

resource "aws_api_gateway_method" "post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.predict.id
  http_method   = "POST"
  authorization = "NONE"
}

##############################################
# Lambda Integration (proxy mode)
##############################################

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.predict.id
  http_method = aws_api_gateway_method.post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"

  # This connects API Gateway → Lambda
  uri = aws_lambda_function.lambda.invoke_arn
}

##############################################
# Permission: API Gateway → Lambda
##############################################

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "apigateway.amazonaws.com"
}

##############################################
# Deployment (makes API callable)
##############################################

resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda
  ]

  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "prod"
}
