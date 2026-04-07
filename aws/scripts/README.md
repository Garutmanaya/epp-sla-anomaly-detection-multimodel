# epp-sla-anomaly-detection-multimodel – CLI Deployment Tool

## Overview

This project includes an **idempotent CLI tool** to deploy, inspect, and clean up a serverless ML inference pipeline on AWS.

The CLI provisions:

* Amazon SageMaker – serverless inference endpoint
* AWS Lambda – request relay layer
* Amazon API Gateway – public API

The system is designed for **multi-model inference** using a single Docker container.

---

## Architecture

```text
Client → API Gateway → Lambda → SageMaker Endpoint → FastAPI (Docker)
```

---

## Key Features

* Idempotent deployment (safe re-run)
* Minimal input: only ECR image required
* Automatic resource reuse (skip if exists)
* Built-in deployment status inspection
* CLI-based alternative to Terraform

---

## Prerequisites

* Python 3.9+
* AWS CLI configured (`aws configure`)
* Docker image pushed to ECR
* IAM roles set via environment variables:

```bash
export SAGEMAKER_ROLE_ARN=arn:aws:iam::<account-id>:role/<role>
export LAMBDA_ROLE_ARN=arn:aws:iam::<account-id>:role/<role>
```

---

## CLI Commands

### 1. Deploy

```bash
python cli.py deploy --ecr-image <ECR_IMAGE_URI>
```

Optional arguments:

```bash
--region        AWS region (default: us-east-1)
--memory        SageMaker memory (default: 2048 MB)
--concurrency   Max concurrency (default: 10)
```

### What happens during deploy

1. Creates SageMaker model
2. Creates endpoint configuration
3. Deploys endpoint (longest step)
4. Creates Lambda function
5. Creates API Gateway

All steps are **idempotent** (existing resources are skipped).

---

### 2. Status (NEW)

```bash
python cli.py status
```

Displays:

* AWS account and caller identity
* SageMaker endpoint status
* Lambda function status
* API Gateway URL
* Ready-to-use curl test command

---

### Example Output

```text
===== DEPLOYMENT STATUS =====

AWS Account: 123456789012
Region     : us-east-1

SageMaker Endpoint:
  Name   : epp-sla-anomaly-detection-multimodel-endpoint
  Status : InService

Lambda:
  Name : epp-sla-anomaly-detection-multimodel-relay

API Gateway:
  URL : https://abc.execute-api.us-east-1.amazonaws.com/prod/predict
```

---

### 3. Test Inference

```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/predict \
  -H "Content-Type: application/json" \
  -d '{"model_name":"test","data":{}}'
```

---

### 4. Cleanup

```bash
python cli.py cleanup
```

Deletes:

* SageMaker endpoint
* Endpoint configuration
* Model
* Lambda function
* API Gateway

---

## Important Notes

### SageMaker Container Requirements

Your Docker image must:

* Listen on port **8080**
* Provide endpoints:

  * `GET /ping`
  * `POST /invocations`
* Include a `serve` entrypoint

---

### Example `serve` script

```bash
#!/bin/bash
exec uvicorn app:app --host 0.0.0.0 --port 8080
```

---

### Common Issues

| Issue                      | Cause                        | Fix                |
| -------------------------- | ---------------------------- | ------------------ |
| Endpoint stuck in Creating | Slow startup / model loading | Optimize container |
| `serve not found`          | Missing entrypoint           | Add serve script   |
| Port issues                | Using 8000                   | Switch to 8080     |
| Module import error        | Wrong working dir            | Set `WORKDIR /app` |

---

## Best Practices

* Keep Docker image size small (<1GB recommended)
* Use lazy model loading for multi-model setup
* Keep `/ping` endpoint lightweight
* Use environment variables for IAM roles

---

## Relationship with Terraform

This CLI mirrors the Terraform deployment:

```text
Model → EndpointConfig → Endpoint → Lambda → API Gateway
```

Use:

* **Terraform** → production infrastructure
* **CLI** → quick testing / iteration

---

## Future Improvements

* Health check validation after deploy
* CloudWatch log links in status output
* Multi-environment support (dev/stage/prod)
* Blue/green endpoint deployments

---

## Summary

This CLI provides a **simple, reproducible way** to deploy and inspect your ML inference pipeline with minimal input and full visibility.

---

