from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

RUNTIME = boto3.client(
    "sagemaker-runtime",
    region_name=os.getenv("AWS_REGION"),
)


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def parse_event(event: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
    if "requestContext" in event:
        request = event["requestContext"].get("http", {})
        method = request.get("method", "GET").upper()
        path = event.get("rawPath") or event.get("path") or "/"
        body = event.get("body")
        payload = None
        if body:
            payload = json.loads(body) if isinstance(body, str) else body
        return method, path, payload

    kind = str(event.get("kind", "health")).lower()
    if kind == "predict":
        return "POST", "/predict", event.get("payload")
    return "GET", "/health", None


def invoke_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    endpoint_name = os.environ["SAGEMAKER_ENDPOINT_NAME"]
    response = RUNTIME.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload).encode("utf-8"),
    )
    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    LOGGER.info("Received event keys: %s", sorted(event.keys()))

    method, path, payload = parse_event(event)

    if method == "GET" and path in {"/", "/health"}:
        return json_response(
            200,
            {
                "status": "ok",
                "endpoint_name": os.environ.get("SAGEMAKER_ENDPOINT_NAME", ""),
                "region": os.environ.get("AWS_REGION", ""),
            },
        )

    if method == "POST" and path == "/predict":
        if not payload:
            return json_response(400, {"error": "Request body is required."})

        try:
            result = invoke_endpoint(payload)
        except Exception as exc:  # pragma: no cover - runtime path
            LOGGER.exception("SageMaker invocation failed")
            return json_response(502, {"error": f"SageMaker invocation failed: {exc}"})

        return json_response(200, result)

    return json_response(404, {"error": f"Unsupported route: {method} {path}"})
