# epp-sla-anomaly-detection-multimodel – Idempotent CLI Deployment

## Overview

This CLI tool deploys a serverless ML inference pipeline on AWS in an **idempotent** manner (safe to re-run).

It provisions:

* Amazon SageMaker (serverless endpoint)
* AWS Lambda (relay)
* Amazon API Gateway (public API)

---

## Key Features

* Idempotent (safe re-run)
* No duplicate resource failures
* Single command deploy + cleanup
* Supports multi-model logic inside container

---

## Architecture

Client → API Gateway → Lambda → SageMaker Serverless → Docker (FastAPI + Models)

---

## Prerequisites

* Python 3.9+
* AWS CLI configured
* ECR image ready
* IAM roles:

  * SageMaker role (ECR access)
  * Lambda role (`InvokeEndpoint`, logs)

---

## Deploy

```bash
python cli.py deploy \
  --ecr-image <ECR_IMAGE_URI> \
  --sagemaker-role <ROLE_ARN> \
  --lambda-role <ROLE_ARN>
```

Optional:

```bash
--memory 2048 --concurrency 10
```

---

## Idempotency Behavior

* Existing resources are skipped
* No failures on re-run
* Safe for CI/CD pipelines

Example:

```bash
python cli.py deploy ...   # creates resources
python cli.py deploy ...   # safely skips existing ones
```

---

## Cleanup

```bash
python cli.py cleanup
```

Deletes all resources created by the CLI.

---

## API Usage

POST /predict

```json
{
  "model_name": "ADD-DOMAIN",
  "data": {}
}
```

---

## Notes

* Model routing handled inside container
* No `TargetModel` used
* Serverless max memory: 6 GB
* No GPU support

---

## Future Improvements

* Resource updates (not just skip)
* Health/status command
* Blue/green deployment
* Observability (logs + tracing)

---

