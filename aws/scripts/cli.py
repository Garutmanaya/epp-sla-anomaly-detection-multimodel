#!/usr/bin/env python3

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

# Optional: fallback roles from env
SAGEMAKER_ROLE = os.getenv("SAGEMAKER_ROLE_ARN")
LAMBDA_ROLE = os.getenv("LAMBDA_ROLE_ARN")


# -----------------------------
# AWS Clients
# -----------------------------
def get_clients(region):
    return {
        "sm": boto3.client("sagemaker", region_name=region),
        "lambda": boto3.client("lambda", region_name=region),
        "apigw": boto3.client("apigateway", region_name=region),
        "sts": boto3.client("sts", region_name=region),
        "iam": boto3.client("iam"),
    }


# -----------------------------
# Utility
# -----------------------------
def exists(fn, **kwargs):
    try:
        fn(**kwargs)
        return True
    except ClientError:
        return False


# -----------------------------
# SageMaker
# -----------------------------
def ensure_model(sm, image):
    if exists(sm.describe_model, ModelName=MODEL_NAME):
        print("[SKIP] Model exists")
        return

    print("[CREATE] Model")
    sm.create_model(
        ModelName=MODEL_NAME,
        ExecutionRoleArn=SAGEMAKER_ROLE,
        PrimaryContainer={"Image": image}
    )


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


def ensure_lambda(lambda_client):
    if exists(lambda_client.get_function, FunctionName=LAMBDA_NAME):
        print("[SKIP] Lambda exists")
        return

    print("[CREATE] Lambda")
    package_lambda()

    with open("lambda.zip", "rb") as f:
        lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.11",
            Role=LAMBDA_ROLE,
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
# STATUS (NEW)
# -----------------------------
def show_status(clients, region):
    sm = clients["sm"]
    lambda_client = clients["lambda"]
    apigw = clients["apigw"]
    sts = clients["sts"]

    print("\n===== DEPLOYMENT STATUS =====\n")

    # AWS identity
    identity = sts.get_caller_identity()
    print(f"AWS Account: {identity['Account']}")
    print(f"Caller ARN : {identity['Arn']}")
    print(f"Region     : {region}\n")

    # SageMaker
    try:
        ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        print("SageMaker Endpoint:")
        print(f"  Name   : {ep['EndpointName']}")
        print(f"  Status : {ep['EndpointStatus']}\n")
    except:
        print("SageMaker Endpoint: NOT FOUND\n")

    # Lambda
    try:
        fn = lambda_client.get_function(FunctionName=LAMBDA_NAME)
        print("Lambda:")
        print(f"  Name : {fn['Configuration']['FunctionName']}\n")
    except:
        print("Lambda: NOT FOUND\n")

    # API Gateway
    api = find_api(apigw)
    if api:
        url = f"https://{api['id']}.execute-api.{region}.amazonaws.com/prod/predict"
        print("API Gateway:")
        print(f"  URL : {url}\n")

        print("Test Command:")
        print(f"""curl -X POST {url} \\
  -H "Content-Type: application/json" \\
  -d '{{"model_name":"test","data":{{}}}}'\n""")
    else:
        print("API Gateway: NOT FOUND\n")


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
# IAM (NEW)
# -----------------------------
def create_role_if_not_exists(iam, role_name, assume_policy):
    try:
        role = iam.get_role(RoleName=role_name)
        print(f"[SKIP] Role exists: {role_name}")
        return role["Role"]["Arn"]
    except ClientError:
        print(f"[CREATE] Role: {role_name}")
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_policy)
        )
        return role["Role"]["Arn"]


def attach_policy(iam, role_name, policy_arn):
    try:
        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except ClientError:
        pass

# -----------------------------
# CREATE ROLES
# -----------------------------
def create_roles(iam):
    print("\n[SETUP] Creating IAM Roles\n")

    # -----------------------------
    # SageMaker Role
    # -----------------------------
    sm_assume = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "sagemaker.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    sm_role_name = f"{PROJECT}-sagemaker-role"
    sm_arn = create_role_if_not_exists(iam, sm_role_name, sm_assume)

    attach_policy(iam, sm_role_name, "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")

    # -----------------------------
    # Lambda Role
    # -----------------------------
    lambda_assume = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    lambda_role_name = f"{PROJECT}-lambda-role"
    lambda_arn = create_role_if_not_exists(iam, lambda_role_name, lambda_assume)

    attach_policy(iam, lambda_role_name,
                  "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

    # Custom inline policy for SageMaker invoke
    iam.put_role_policy(
        RoleName=lambda_role_name,
        PolicyName="invoke-sagemaker",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "sagemaker:InvokeEndpoint",
                "Resource": "*"
            }]
        })
    )

    print("\n[OUTPUT]")
    print(f"SAGEMAKER_ROLE_ARN={sm_arn}")
    print(f"LAMBDA_ROLE_ARN={lambda_arn}")

    print("\nExport these before deploy:")
    print(f"export SAGEMAKER_ROLE_ARN={sm_arn}")
    print(f"export LAMBDA_ROLE_ARN={lambda_arn}")

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(dest="cmd")

    # DEPLOY
    d = sub.add_parser("deploy")
    d.add_argument("--region", default="us-east-1")
    d.add_argument("--ecr-image", required=True)
    d.add_argument("--memory", type=int, default=2048)
    d.add_argument("--concurrency", type=int, default=10)

    # CREATE ROLES (NEW)
    r = sub.add_parser("create-roles")
    r.add_argument("--region", default="us-east-1")

    # CLEANUP
    c = sub.add_parser("cleanup")
    c.add_argument("--region", default="us-east-1")

    # STATUS (NEW)
    s = sub.add_parser("status")
    s.add_argument("--region", default="us-east-1")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    clients = get_clients(args.region)

    if args.cmd == "deploy":
        if not SAGEMAKER_ROLE or not LAMBDA_ROLE:
            print("[ERROR] Missing IAM roles.")
            print("Run: python cli.py create-roles")
            print("Then export SAGEMAKER_ROLE_ARN and LAMBDA_ROLE_ARN")
            sys.exit(1)
        ensure_model(clients["sm"], args.ecr_image)
        ensure_endpoint_config(clients["sm"], args.memory, args.concurrency)
        ensure_endpoint(clients["sm"])
        ensure_lambda(clients["lambda"])
        ensure_api(clients["apigw"], clients["lambda"], args.region)

    elif args.cmd == "cleanup":
        cleanup(clients)

    elif args.cmd == "status":
        show_status(clients, args.region)
        
    elif args.cmd == "create-roles":
        create_roles(clients["iam"])


if __name__ == "__main__":
    main()
