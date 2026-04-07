# Lambda acts as a relay between API Gateway and SageMaker

import json
import boto3
import os

# Create SageMaker runtime client
runtime = boto3.client("sagemaker-runtime")

# Endpoint name passed from Terraform
ENDPOINT_NAME = os.environ["ENDPOINT_NAME"]

def lambda_handler(event, context):
    """
    Receives HTTP request from API Gateway
    Forwards payload to SageMaker endpoint
    Returns inference result
    """

    body = json.loads(event.get("body", "{}"))

    response = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=json.dumps(body)
    )

    return {
        "statusCode": 200,
        "body": response["Body"].read().decode()
    }
