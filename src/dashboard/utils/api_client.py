

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
def build_api_url(path_key: str) -> str:
    """
    Build API URL from config.

    Args:
        path_key: "predict_path" or "compare_path"

    Returns:
        Full URL string
    """
    cfg = load_main_config()
    api_cfg = get_api_config(cfg)

    return api_cfg["base_url"] + api_cfg[path_key]


# =========================================
# CALL FASTAPI (LOCAL / DEV)
# =========================================
def call_rest_api(payload: dict, path_key: str) -> dict:
    """
    Call FastAPI endpoint.

    Args:
        payload: request payload
        path_key: config key for endpoint path

    Returns:
        JSON response dict
    """
    url = build_api_url(path_key)

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
    Call SageMaker endpoint using boto3.

    Args:
        payload: request payload

    Returns:
        JSON response dict (normalized)
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

    # SageMaker returns streaming body → decode
    result = json.loads(response["Body"].read())

    return result


# =========================================
# MAIN ENTRY: UNIFIED CALL
# =========================================
def call_inference(payload: dict, mode: str = "predict") -> dict:
    """
    Unified inference call.

    Automatically switches between:
    - FastAPI (local)
    - SageMaker (production)

    Args:
        payload: request payload
        mode: "predict" or "compare"

    Returns:
        dict:
            {
                "results": [...]
            }
    """
    cfg = load_main_config()
    sm_cfg = get_sagemaker_config(cfg)

    try:
        # =====================================
        # SAGEMAKER PATH
        # =====================================
        if sm_cfg.get("enabled"):

            response = call_sagemaker(payload)

        # =====================================
        # FASTAPI PATH
        # =====================================
        else:

            path_key = "predict_path" if mode == "predict" else "compare_path"
            response = call_rest_api(payload, path_key)

        # =====================================
        # NORMALIZE RESPONSE
        # =====================================

        # Case 1: single model (standard)
        if "results" in response:
            return response

        # Case 2: compare API (multi-model)
        if all(isinstance(v, list) for v in response.values()):
            return response

        # Case 3: raw list fallback
        if isinstance(response, list):
            return {"results": response}

        # Otherwise invalid
        raise ValueError(f"Invalid response format: {type(response)}")
        

    except Exception as e:
        raise RuntimeError(f"Inference call failed: {str(e)}")
