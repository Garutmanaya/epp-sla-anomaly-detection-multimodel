##############################################
# Core AWS configuration
##############################################

variable "region" {
  description = "AWS region for all resources"
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS account ID (used for ECR image URI if needed)"
}

##############################################
# ECR Image (your custom container)
##############################################

variable "ecr_image" {
  description = "Full ECR image URI (must include tag)"
  # Example:
  # 123456789012.dkr.ecr.us-east-1.amazonaws.com/anomaly:latest
}

##############################################
# IAM Roles (must already exist)
##############################################

variable "sagemaker_role_arn" {
  description = "IAM role ARN used by SageMaker to pull ECR + run container"
}

variable "lambda_role_arn" {
  description = "IAM role ARN used by Lambda (must allow InvokeEndpoint + logs)"
}

##############################################
# Serverless configuration
##############################################

variable "memory_size" {
  description = "Memory size for serverless inference (MB)"
  default     = 2048
}

variable "max_concurrency" {
  description = "Max concurrent invocations"
  default     = 10
}
