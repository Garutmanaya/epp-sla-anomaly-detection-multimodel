import json
import boto3
import os

# SageMaker runtime client
runtime = boto3.client("sagemaker-runtime")

# Endpoint name injected via Terraform
ENDPOINT_NAME = os.environ["ENDPOINT_NAME"]

def lambda_handler(event, context):
    """
    API Gateway → Lambda → SageMaker flow

    Expected input:
    {
        "model_name": "...",
        "data": ...
    }
    """

    try:
        body = json.loads(event.get("body", "{}"))

        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(body)
        )

        result = response["Body"].read().decode()

        return {
            "statusCode": 200,
            "body": result
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }
