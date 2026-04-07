from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import io
import json
import time
from pathlib import Path
from typing import Any
import zipfile

import boto3
from botocore.exceptions import ClientError, WaiterError

REPO_ROOT = Path(__file__).resolve().parents[1]
LAMBDA_HANDLER_PATH = REPO_ROOT / "infra" / "lambda" / "sagemaker_relay" / "handler.py"
MANAGED_TAG_KEY = "managed-by"
MANAGED_TAG_VALUE = "epp-sla-demo-scripts"


@dataclass(frozen=True)
class StackConfig:
    region: str
    stack_name: str
    image_uri: str
    sagemaker_execution_role_arn: str
    endpoint_name: str
    model_prefix: str
    endpoint_config_prefix: str
    lambda_function_name: str
    lambda_role_name: str
    lambda_role_arn: str | None
    create_lambda_role: bool
    api_name: str
    sagemaker_serverless_memory_mb: int
    sagemaker_serverless_max_concurrency: int
    sagemaker_provisioned_concurrency: int | None
    lambda_timeout_seconds: int
    lambda_memory_mb: int
    lambda_log_level: str
    gateway_health_path: str
    gateway_predict_path: str
    output_json_path: Path | None
    tags: dict[str, str]
    container_environment: dict[str, str]


def build_stack_config(args: Any) -> StackConfig:
    stack_name = args.stack_name
    tags = {
        MANAGED_TAG_KEY: MANAGED_TAG_VALUE,
        "stack-name": stack_name,
    }

    return StackConfig(
        region=args.region,
        stack_name=stack_name,
        image_uri=args.image_uri,
        sagemaker_execution_role_arn=args.sagemaker_execution_role_arn,
        endpoint_name=args.endpoint_name or f"{stack_name}-endpoint",
        model_prefix=args.model_prefix or f"{stack_name}-model",
        endpoint_config_prefix=args.endpoint_config_prefix or f"{stack_name}-config",
        lambda_function_name=args.lambda_function_name or f"{stack_name}-relay",
        lambda_role_name=args.lambda_role_name or f"{stack_name}-relay-role",
        lambda_role_arn=args.lambda_role_arn,
        create_lambda_role=not bool(args.lambda_role_arn),
        api_name=args.api_name or f"{stack_name}-http-api",
        sagemaker_serverless_memory_mb=args.sagemaker_serverless_memory_mb,
        sagemaker_serverless_max_concurrency=args.sagemaker_serverless_max_concurrency,
        sagemaker_provisioned_concurrency=args.sagemaker_provisioned_concurrency,
        lambda_timeout_seconds=args.lambda_timeout_seconds,
        lambda_memory_mb=args.lambda_memory_mb,
        lambda_log_level=args.lambda_log_level,
        gateway_health_path=normalize_path(args.gateway_health_path or "/health"),
        gateway_predict_path=normalize_path(args.gateway_predict_path or "/predict"),
        output_json_path=Path(args.output_json_path).resolve() if args.output_json_path else None,
        tags=tags,
        container_environment=parse_key_value_pairs(args.container_env or []),
    )


def normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def parse_key_value_pairs(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE format, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Environment variable key cannot be empty: {item}")
        parsed[key] = value
    return parsed


def timestamp_suffix() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")


def to_sagemaker_tags(tags: dict[str, str]) -> list[dict[str, str]]:
    return [{"Key": key, "Value": value} for key, value in sorted(tags.items())]


def session(region: str):
    return boto3.Session(region_name=region)


def sagemaker_client(region: str):
    return session(region).client("sagemaker")


def sagemaker_runtime_client(region: str):
    return session(region).client("sagemaker-runtime")


def lambda_client(region: str):
    return session(region).client("lambda")


def iam_client(region: str):
    return session(region).client("iam")


def apigatewayv2_client(region: str):
    return session(region).client("apigatewayv2")


def sts_client(region: str):
    return session(region).client("sts")


def account_id(region: str) -> str:
    return sts_client(region).get_caller_identity()["Account"]


def format_endpoint_arn(config: StackConfig) -> str:
    return f"arn:aws:sagemaker:{config.region}:{account_id(config.region)}:endpoint/{config.endpoint_name}"


def ensure_lambda_role(config: StackConfig) -> tuple[str, bool]:
    if config.lambda_role_arn:
        return config.lambda_role_arn, False

    client = iam_client(config.region)
    role_name = config.lambda_role_name
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    endpoint_arn = format_endpoint_arn(config)
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": "arn:aws:logs:*:*:*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sagemaker:InvokeEndpoint",
                    "sagemaker:DescribeEndpoint",
                ],
                "Resource": endpoint_arn,
            },
        ],
    }

    role_created = False
    try:
        response = client.get_role(RoleName=role_name)
        role_arn = response["Role"]["Arn"]
    except client.exceptions.NoSuchEntityException:
        response = client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Lambda role for relaying demo requests to SageMaker endpoints.",
            Tags=[{"Key": key, "Value": value} for key, value in config.tags.items()],
        )
        role_arn = response["Role"]["Arn"]
        role_created = True
        time.sleep(10)

    client.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{role_name}-inline",
        PolicyDocument=json.dumps(inline_policy),
    )

    return role_arn, role_created


def delete_lambda_role(config: StackConfig) -> None:
    if config.lambda_role_arn:
        return

    client = iam_client(config.region)
    role_name = config.lambda_role_name

    try:
        policies = client.list_role_policies(RoleName=role_name)["PolicyNames"]
    except client.exceptions.NoSuchEntityException:
        return

    for policy_name in policies:
        client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

    client.delete_role(RoleName=role_name)


def load_lambda_zip_bytes() -> bytes:
    source = LAMBDA_HANDLER_PATH.read_text()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handler.py", source)
    return buffer.getvalue()


def lambda_environment(config: StackConfig) -> dict[str, str]:
    return {
        "AWS_REGION": config.region,
        "SAGEMAKER_ENDPOINT_NAME": config.endpoint_name,
        "LOG_LEVEL": config.lambda_log_level,
    }


def wait_for_lambda_active(config: StackConfig) -> None:
    client = lambda_client(config.region)
    for _ in range(60):
        response = client.get_function_configuration(FunctionName=config.lambda_function_name)
        state = response.get("State")
        last_update_status = response.get("LastUpdateStatus")
        if state == "Active" and last_update_status in {None, "Successful"}:
            return
        if state == "Failed" or last_update_status == "Failed":
            raise RuntimeError(f"Lambda deployment failed: {response}")
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for Lambda function {config.lambda_function_name} to become active.")


def ensure_lambda_function(config: StackConfig, role_arn: str) -> dict[str, Any]:
    client = lambda_client(config.region)
    zip_bytes = load_lambda_zip_bytes()

    kwargs = {
        "FunctionName": config.lambda_function_name,
        "Runtime": "python3.12",
        "Role": role_arn,
        "Handler": "handler.lambda_handler",
        "Code": {"ZipFile": zip_bytes},
        "Description": "Demo relay for API Gateway -> Lambda -> SageMaker flow.",
        "Timeout": config.lambda_timeout_seconds,
        "MemorySize": config.lambda_memory_mb,
        "Publish": True,
        "Environment": {"Variables": lambda_environment(config)},
        "Architectures": ["x86_64"],
        "Tags": config.tags,
    }

    try:
        response = client.get_function(FunctionName=config.lambda_function_name)
        revision_id = response["Configuration"]["RevisionId"]
        client.update_function_configuration(
            FunctionName=config.lambda_function_name,
            Role=role_arn,
            Timeout=config.lambda_timeout_seconds,
            MemorySize=config.lambda_memory_mb,
            Environment={"Variables": lambda_environment(config)},
            Description=kwargs["Description"],
        )
        wait_for_lambda_active(config)
        client.update_function_code(
            FunctionName=config.lambda_function_name,
            ZipFile=zip_bytes,
            Publish=True,
            RevisionId=revision_id,
        )
    except client.exceptions.ResourceNotFoundException:
        client.create_function(**kwargs)

    wait_for_lambda_active(config)
    return client.get_function(FunctionName=config.lambda_function_name)["Configuration"]


def delete_lambda_function(config: StackConfig) -> None:
    client = lambda_client(config.region)
    try:
        client.delete_function(FunctionName=config.lambda_function_name)
    except client.exceptions.ResourceNotFoundException:
        return


def latest_sagemaker_names(config: StackConfig) -> tuple[str, str]:
    suffix = timestamp_suffix()
    return f"{config.model_prefix}-{suffix}", f"{config.endpoint_config_prefix}-{suffix}"


def deploy_sagemaker_endpoint(config: StackConfig) -> dict[str, str]:
    client = sagemaker_client(config.region)
    model_name, endpoint_config_name = latest_sagemaker_names(config)

    primary_container: dict[str, Any] = {
        "Image": config.image_uri,
    }
    if config.container_environment:
        primary_container["Environment"] = config.container_environment

    client.create_model(
        ModelName=model_name,
        ExecutionRoleArn=config.sagemaker_execution_role_arn,
        PrimaryContainer=primary_container,
        Tags=to_sagemaker_tags(config.tags),
    )

    production_variant: dict[str, Any] = {
        "VariantName": "AllTraffic",
        "ModelName": model_name,
        "ServerlessConfig": {
            "MemorySizeInMB": config.sagemaker_serverless_memory_mb,
            "MaxConcurrency": config.sagemaker_serverless_max_concurrency,
        },
    }
    if config.sagemaker_provisioned_concurrency is not None:
        production_variant["ServerlessConfig"]["ProvisionedConcurrency"] = config.sagemaker_provisioned_concurrency

    client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[production_variant],
        Tags=to_sagemaker_tags(config.tags),
    )

    endpoint_exists = False
    try:
        client.describe_endpoint(EndpointName=config.endpoint_name)
        endpoint_exists = True
    except client.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] != "ValidationException":
            raise

    if endpoint_exists:
        client.update_endpoint(
            EndpointName=config.endpoint_name,
            EndpointConfigName=endpoint_config_name,
        )
    else:
        client.create_endpoint(
            EndpointName=config.endpoint_name,
            EndpointConfigName=endpoint_config_name,
            Tags=to_sagemaker_tags(config.tags),
        )

    wait_for_endpoint(config.region, config.endpoint_name)

    return {
        "model_name": model_name,
        "endpoint_config_name": endpoint_config_name,
        "endpoint_name": config.endpoint_name,
    }


def wait_for_endpoint(region: str, endpoint_name: str) -> None:
    client = sagemaker_client(region)
    waiter = client.get_waiter("endpoint_in_service")
    try:
        waiter.wait(EndpointName=endpoint_name, WaiterConfig={"Delay": 15, "MaxAttempts": 80})
    except WaiterError as exc:
        details = client.describe_endpoint(EndpointName=endpoint_name)
        raise RuntimeError(f"SageMaker endpoint failed to reach InService: {details}") from exc


def delete_endpoint_and_wait(region: str, endpoint_name: str) -> None:
    client = sagemaker_client(region)
    try:
        client.delete_endpoint(EndpointName=endpoint_name)
    except client.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "ValidationException":
            return
        raise

    waiter = client.get_waiter("endpoint_deleted")
    waiter.wait(EndpointName=endpoint_name, WaiterConfig={"Delay": 15, "MaxAttempts": 80})


def list_endpoint_configs_by_prefix(region: str, prefix: str) -> list[str]:
    client = sagemaker_client(region)
    names: list[str] = []
    next_token: str | None = None
    while True:
        kwargs = {"NameContains": prefix}
        if next_token:
            kwargs["NextToken"] = next_token
        response = client.list_endpoint_configs(**kwargs)
        names.extend(item["EndpointConfigName"] for item in response.get("EndpointConfigs", []))
        next_token = response.get("NextToken")
        if not next_token:
            return names


def list_models_by_prefix(region: str, prefix: str) -> list[str]:
    client = sagemaker_client(region)
    names: list[str] = []
    next_token: str | None = None
    while True:
        kwargs = {"NameContains": prefix}
        if next_token:
            kwargs["NextToken"] = next_token
        response = client.list_models(**kwargs)
        names.extend(item["ModelName"] for item in response.get("Models", []))
        next_token = response.get("NextToken")
        if not next_token:
            return names


def delete_sagemaker_resources(config: StackConfig) -> None:
    delete_endpoint_and_wait(config.region, config.endpoint_name)
    client = sagemaker_client(config.region)

    for endpoint_config_name in list_endpoint_configs_by_prefix(config.region, config.endpoint_config_prefix):
        try:
            client.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        except client.exceptions.ClientError:
            pass

    for model_name in list_models_by_prefix(config.region, config.model_prefix):
        try:
            client.delete_model(ModelName=model_name)
        except client.exceptions.ClientError:
            pass


def get_api_by_name(region: str, api_name: str) -> dict[str, Any] | None:
    client = apigatewayv2_client(region)
    next_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {}
        if next_token:
            kwargs["NextToken"] = next_token
        response = client.get_apis(**kwargs)
        for api in response.get("Items", []):
            if api["Name"] == api_name:
                return api
        next_token = response.get("NextToken")
        if not next_token:
            return None


def ensure_http_api(config: StackConfig) -> dict[str, Any]:
    client = apigatewayv2_client(config.region)
    api = get_api_by_name(config.region, config.api_name)
    if api is None:
        api = client.create_api(
            Name=config.api_name,
            ProtocolType="HTTP",
            CorsConfiguration={
                "AllowOrigins": ["*"],
                "AllowMethods": ["GET", "POST", "OPTIONS"],
                "AllowHeaders": ["content-type"],
                "MaxAge": 3600,
            },
            Tags=config.tags,
        )

    stage_name = "$default"
    try:
        client.get_stage(ApiId=api["ApiId"], StageName=stage_name)
    except client.exceptions.NotFoundException:
        client.create_stage(
            ApiId=api["ApiId"],
            StageName=stage_name,
            AutoDeploy=True,
            Tags=config.tags,
        )
    else:
        client.update_stage(ApiId=api["ApiId"], StageName=stage_name, AutoDeploy=True)

    return api


def ensure_http_api_integration(config: StackConfig, api_id: str, function_arn: str) -> str:
    client = apigatewayv2_client(config.region)
    integration_uri = (
        f"arn:aws:apigateway:{config.region}:lambda:path/2015-03-31/functions/{function_arn}/invocations"
    )

    integrations = client.get_integrations(ApiId=api_id).get("Items", [])
    for integration in integrations:
        if integration.get("IntegrationUri") == integration_uri:
            return integration["IntegrationId"]

    response = client.create_integration(
        ApiId=api_id,
        IntegrationType="AWS_PROXY",
        IntegrationMethod="POST",
        IntegrationUri=integration_uri,
        PayloadFormatVersion="2.0",
        TimeoutInMillis=29000,
    )
    return response["IntegrationId"]


def ensure_http_route(region: str, api_id: str, route_key: str, integration_id: str) -> None:
    client = apigatewayv2_client(region)
    target = f"integrations/{integration_id}"
    routes = client.get_routes(ApiId=api_id).get("Items", [])
    for route in routes:
        if route.get("RouteKey") == route_key:
            client.update_route(ApiId=api_id, RouteId=route["RouteId"], Target=target)
            return

    client.create_route(ApiId=api_id, RouteKey=route_key, Target=target)


def ensure_lambda_permission_for_api(config: StackConfig, api_id: str) -> None:
    client = lambda_client(config.region)
    statement_id = f"{api_id}-invoke"
    source_arn = f"arn:aws:execute-api:{config.region}:{account_id(config.region)}:{api_id}/*/*"

    try:
        client.add_permission(
            FunctionName=config.lambda_function_name,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )
    except client.exceptions.ResourceConflictException:
        return


def deploy_http_api(config: StackConfig) -> dict[str, str]:
    api = ensure_http_api(config)
    function_arn = lambda_client(config.region).get_function(
        FunctionName=config.lambda_function_name
    )["Configuration"]["FunctionArn"]
    integration_id = ensure_http_api_integration(config, api["ApiId"], function_arn)
    ensure_http_route(config.region, api["ApiId"], f"GET {config.gateway_health_path}", integration_id)
    ensure_http_route(config.region, api["ApiId"], f"POST {config.gateway_predict_path}", integration_id)
    ensure_lambda_permission_for_api(config, api["ApiId"])

    return {
        "api_id": api["ApiId"],
        "api_name": api["Name"],
        "api_endpoint": api["ApiEndpoint"],
        "health_url": f"{api['ApiEndpoint']}{config.gateway_health_path}",
        "predict_url": f"{api['ApiEndpoint']}{config.gateway_predict_path}",
    }


def delete_http_api(config: StackConfig) -> None:
    client = apigatewayv2_client(config.region)
    api = get_api_by_name(config.region, config.api_name)
    if api is None:
        return
    client.delete_api(ApiId=api["ApiId"])


def invoke_sagemaker_prediction(config: StackConfig, payload: dict[str, Any]) -> dict[str, Any]:
    response = sagemaker_runtime_client(config.region).invoke_endpoint(
        EndpointName=config.endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload).encode("utf-8"),
    )
    return json.loads(response["Body"].read().decode("utf-8"))


def invoke_lambda_prediction(config: StackConfig, payload: dict[str, Any]) -> dict[str, Any]:
    client = lambda_client(config.region)
    response = client.invoke(
        FunctionName=config.lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"kind": "predict", "payload": payload}).encode("utf-8"),
    )
    response_payload = json.loads(response["Payload"].read().decode("utf-8"))
    if "statusCode" in response_payload:
        return json.loads(response_payload["body"])
    return response_payload


def invoke_lambda_health(config: StackConfig) -> dict[str, Any]:
    client = lambda_client(config.region)
    response = client.invoke(
        FunctionName=config.lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"kind": "health"}).encode("utf-8"),
    )
    payload = json.loads(response["Payload"].read().decode("utf-8"))
    if "statusCode" in payload:
        return json.loads(payload["body"])
    return payload


def sample_payload() -> dict[str, Any]:
    return {
        "models": ["xgboost", "isolationforest"],
        "data": [
            {
                "timestamp": "2026-04-01T00:00:00Z",
                "command": "CHECK-DOMAIN",
                "success_vol": 1400.0,
                "success_rt_avg": 122.3,
                "fail_vol": 4.0,
                "fail_rt_avg": 301.2,
            },
            {
                "timestamp": "2026-04-01T01:00:00Z",
                "command": "CHECK-DOMAIN",
                "success_vol": 1388.0,
                "success_rt_avg": 118.1,
                "fail_vol": 3.0,
                "fail_rt_avg": 297.4,
            },
            {
                "timestamp": "2026-04-01T02:00:00Z",
                "command": "CHECK-DOMAIN",
                "success_vol": 1465.0,
                "success_rt_avg": 181.4,
                "fail_vol": 19.0,
                "fail_rt_avg": 442.8,
            },
        ],
    }


def write_outputs(config: StackConfig, outputs: dict[str, Any]) -> None:
    if config.output_json_path is None:
        return

    config.output_json_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_json_path.write_text(json.dumps(outputs, indent=2, sort_keys=True))


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def safe_delete_http_api(config: StackConfig) -> None:
    try:
        delete_http_api(config)
    except ClientError:
        pass


def safe_delete_lambda_function(config: StackConfig) -> None:
    try:
        delete_lambda_function(config)
    except ClientError:
        pass


def safe_delete_lambda_role(config: StackConfig) -> None:
    try:
        delete_lambda_role(config)
    except ClientError:
        pass


def safe_delete_sagemaker_resources(config: StackConfig) -> None:
    try:
        delete_sagemaker_resources(config)
    except ClientError:
        pass
