# =========================================
# MODULE: api_client
# PURPOSE: Unified inference client for
#          FastAPI (local) and SageMaker (prod)
# =========================================

# =========================================
# IMPORTS
# =========================================
import json
import requests

from common.config_loader import (
    load_main_config,
    get_api_config,
    get_sagemaker_config
)

# =========================================
# CONSTANTS
# =========================================
DEFAULT_TIMEOUT = 30  # seconds


# =========================================
# BUILD API URL (FASTAPI)
# =========================================
def build_api_url() -> str:
    """
    Build unified API URL (predict endpoint only)
    """
    cfg = load_main_config()
    api_cfg = get_api_config(cfg)

    return api_cfg["base_url"] + api_cfg["predict_path"]


# =========================================
# CALL FASTAPI (LOCAL / DEV)
# =========================================
def call_rest_api(payload: dict) -> dict:
    """
    Call FastAPI predict endpoint
    """
    url = build_api_url()

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=DEFAULT_TIMEOUT
    )

    response.raise_for_status()

    return response.json()


# =========================================
# CALL SAGEMAKER ENDPOINT
# =========================================
def call_sagemaker(payload: dict) -> dict:
    """
    Call SageMaker endpoint
    """
    import boto3

    cfg = load_main_config()
    sm_cfg = get_sagemaker_config(cfg)

    client = boto3.client(
        "sagemaker-runtime",
        region_name=sm_cfg["region"]
    )

    response = client.invoke_endpoint(
        EndpointName=sm_cfg["endpoint_name"],
        ContentType="application/json",
        Body=json.dumps(payload)
    )

    return json.loads(response["Body"].read())


# =========================================
# MAIN ENTRY
# =========================================
def call_inference(payload: dict) -> dict:
    """
    Unified inference call (single + multi model)

    Payload format:
    {
        "models": ["xgboost", "isolationforest"],
        "data": [...]
    }

    Returns:
    {
        "results": {...},
        "metadata": {...}
    }
    """
    cfg = load_main_config()
    sm_cfg = get_sagemaker_config(cfg)

    try:

        # -------------------------------------
        # SAGEMAKER
        # -------------------------------------
        if sm_cfg.get("enabled"):
            response = call_sagemaker(payload)

        # -------------------------------------
        # FASTAPI
        # -------------------------------------
        else:
            response = call_rest_api(payload)

        # -------------------------------------
        # VALIDATION
        # -------------------------------------
        if "results" not in response:
            raise ValueError("Invalid response format: missing 'results'")

        return response

    except Exception as e:
        raise RuntimeError(f"Inference call failed: {str(e)}")