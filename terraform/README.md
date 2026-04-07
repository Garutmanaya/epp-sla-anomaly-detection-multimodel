# epp-sla-anomaly-detection-multimodel – Serverless Deployment

## Overview

This project provisions a fully serverless inference pipeline on AWS using Terraform. A custom Docker image (hosted in ECR) contains the trained anomaly detection models and FastAPI endpoints (`/ping`, `/invocations`). The infrastructure exposes this model via a public API.

## Architecture

```
Client → API Gateway → Lambda → SageMaker Serverless Endpoint → Docker (FastAPI + Models)
```

* **SageMaker Serverless Endpoint** runs the containerized model without managing infrastructure.
* **Lambda** acts as a lightweight relay between API Gateway and SageMaker.
* **API Gateway** provides a public HTTP endpoint (`/predict`).

## Key Features

* Fully serverless (no instance management)
* Pay-per-use inference
* Single endpoint supporting multiple models (handled inside container)
* Infrastructure-as-Code using Terraform
* Clean deployment and teardown

## Prerequisites

* AWS account
* Terraform installed
* Pre-built Docker image pushed to ECR
* IAM roles:

  * SageMaker execution role (ECR access)
  * Lambda execution role (`InvokeEndpoint`, logging)

## Deployment

Initialize and apply Terraform:

```
terraform init

terraform apply \
  -var="account_id=YOUR_ACCOUNT_ID" \
  -var="ecr_image=YOUR_ECR_IMAGE_URI" \
  -var="sagemaker_role_arn=YOUR_SAGEMAKER_ROLE" \
  -var="lambda_role_arn=YOUR_LAMBDA_ROLE"
```

After deployment, Terraform outputs the API endpoint URL.

## API Usage

POST request:

```
POST /predict
Content-Type: application/json
```

Example payload:

```
{
  "model_name": "ADD-DOMAIN",
  "data": { ... }
}
```

The request is forwarded to SageMaker and processed by your FastAPI container.

## Cleanup

To remove all resources:

```
terraform destroy
```

This deletes:

* API Gateway
* Lambda function
* SageMaker endpoint, config, and model

## Notes

* Ensure container startup time is optimized (serverless cold start sensitivity)
* Maximum memory for serverless endpoint is 6 GB
* No GPU support in serverless mode
* Model selection logic must be implemented inside the container

## Future Enhancements

* Authentication (IAM / JWT)
* Custom domain for API Gateway
* CI/CD pipeline for automated deployment
* Multi-environment support (dev/stage/prod)

---

