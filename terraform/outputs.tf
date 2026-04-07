##############################################
# Final API endpoint
##############################################

output "api_url" {
  description = "Invoke URL for inference"
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com/prod/predict"
}

output "sagemaker_endpoint_name" {
  value = aws_sagemaker_endpoint.endpoint.name
}
