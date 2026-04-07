#!/usr/bin/env python3
"""
Idempotent CLI for:
epp-sla-anomaly-detection-multimodel

Features:
- Safe re-run (no duplicate failures)
- Skips existing resources
- Minimal update logic
"""

import argparse
import boto3
import time
import json
import zipfile
import os
import sys
from botocore.exceptions import ClientError

PROJECT = "epp-sla-anomaly-detection-multimodel"

MODEL_NAME = f"{PROJECT}-model"
ENDPOINT_CONFIG = f"{PROJECT}-config"
ENDPOINT_NAME = f"{PROJECT}-endpoint"
LAMBDA_NAME = f"{PROJECT}-relay"
API_NAME = f"{PROJECT}-api"


# -----------------------------
# AWS Clients
# -----------------------------
def get_clients(region):
    return {
        "sm": boto3.client("sagemaker", region_name=region),
        "lambda": boto3.client("lambda", region_name=region),
        "apigw": boto3.client("apigateway", region_name=region),
    }


# -----------------------------
# Utility: existence checks
# -----------------------------
def exists(fn, **kwargs):
    try:
        fn(**kwargs)
        return True
    except ClientError:
        return False


# -----------------------------
# SageMaker Model
# -----------------------------
def ensure_model(sm, image, role):
    if exists(sm.describe_model, ModelName=MODEL_NAME):
        print("[SKIP] Model exists")
        return

    print("[CREATE] Model")
    sm.create_model(
        ModelName=MODEL_NAME,
        ExecutionRoleArn=role,
        PrimaryContainer={"Image": image}
    )


# -----------------------------
# Endpoint Config
# -----------------------------
def ensure_endpoint_config(sm, memory, concurrency):
    if exists(sm.describe_endpoint_config, EndpointConfigName=ENDPOINT_CONFIG):
        print("[SKIP] Endpoint config exists")
        return

    print("[CREATE] Endpoint config")
    sm.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": MODEL_NAME,
            "ServerlessConfig": {
                "MemorySizeInMB": memory,
                "MaxConcurrency": concurrency
            }
        }]
    )


# -----------------------------
# Endpoint
# -----------------------------
def ensure_endpoint(sm):
    if exists(sm.describe_endpoint, EndpointName=ENDPOINT_NAME):
        print("[SKIP] Endpoint exists")
        return

    print("[CREATE] Endpoint")
    sm.create_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=ENDPOINT_CONFIG
    )

    while True:
        status = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
        print("[WAIT]", status)
        if status == "InService":
            break
        time.sleep(15)


# -----------------------------
# Lambda
# -----------------------------
def package_lambda():
    with zipfile.ZipFile("lambda.zip", "w") as z:
        z.write("lambda_handler.py")


def ensure_lambda(lambda_client, role):
    if exists(lambda_client.get_function, FunctionName=LAMBDA_NAME):
        print("[SKIP] Lambda exists")
        return

    print("[CREATE] Lambda")
    package_lambda()

    with open("lambda.zip", "rb") as f:
        lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.11",
            Role=role,
            Handler="lambda_handler.lambda_handler",
            Code={"ZipFile": f.read()},
            Timeout=30,
            MemorySize=512,
            Environment={
                "Variables": {"ENDPOINT_NAME": ENDPOINT_NAME}
            }
        )


# -----------------------------
# API Gateway
# -----------------------------
def find_api(apigw):
    for api in apigw.get_rest_apis()["items"]:
        if api["name"] == API_NAME:
            return api
    return None


def ensure_api(apigw, lambda_client, region):
    api = find_api(apigw)

    if api:
        print("[SKIP] API exists")
        api_id = api["id"]
    else:
        print("[CREATE] API Gateway")
        api = apigw.create_rest_api(name=API_NAME)
        api_id = api["id"]

        root = apigw.get_resources(restApiId=api_id)["items"][0]["id"]

        resource = apigw.create_resource(
            restApiId=api_id,
            parentId=root,
            pathPart="predict"
        )

        apigw.put_method(
            restApiId=api_id,
            resourceId=resource["id"],
            httpMethod="POST",
            authorizationType="NONE"
        )

        lambda_arn = lambda_client.get_function(
            FunctionName=LAMBDA_NAME
        )["Configuration"]["FunctionArn"]

        uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

        apigw.put_integration(
            restApiId=api_id,
            resourceId=resource["id"],
            httpMethod="POST",
            type="AWS_PROXY",
            integrationHttpMethod="POST",
            uri=uri
        )

        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_NAME,
                StatementId="apigw-permission",
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com"
            )
        except ClientError:
            pass

        apigw.create_deployment(restApiId=api_id, stageName="prod")

    print(f"[INFO] API URL: https://{api_id}.execute-api.{region}.amazonaws.com/prod/predict")


# -----------------------------
# Cleanup
# -----------------------------
def cleanup(clients):
    sm = clients["sm"]
    lambda_client = clients["lambda"]
    apigw = clients["apigw"]

    print("[CLEANUP]")

    for fn, args in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": ENDPOINT_CONFIG}),
        (sm.delete_model, {"ModelName": MODEL_NAME}),
    ]:
        try:
            fn(**args)
            print("[DELETE]", args)
        except:
            pass

    try:
        lambda_client.delete_function(FunctionName=LAMBDA_NAME)
    except:
        pass

    api = find_api(apigw)
    if api:
        apigw.delete_rest_api(restApiId=api["id"])


# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(dest="cmd")

    d = sub.add_parser("deploy")
    d.add_argument("--region", default="us-east-1")
    d.add_argument("--ecr-image", required=True)
    d.add_argument("--sagemaker-role", required=True)
    d.add_argument("--lambda-role", required=True)
    d.add_argument("--memory", type=int, default=2048)
    d.add_argument("--concurrency", type=int, default=10)

    c = sub.add_parser("cleanup")
    c.add_argument("--region", default="us-east-1")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    clients = get_clients(args.region)

    if args.cmd == "deploy":
        ensure_model(clients["sm"], args.ecr_image, args.sagemaker_role)
        ensure_endpoint_config(clients["sm"], args.memory, args.concurrency)
        ensure_endpoint(clients["sm"])
        ensure_lambda(clients["lambda"], args.lambda_role)
        ensure_api(clients["apigw"], clients["lambda"], args.region)

    elif args.cmd == "cleanup":
        cleanup(clients)


if __name__ == "__main__":
    main()
