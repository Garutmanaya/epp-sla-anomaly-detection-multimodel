# =========================================
# MODULE: local_utils (XGBoost specific)
# PURPOSE: Encapsulate model-specific paths
# =========================================

from pathlib import Path
from common.config_loader import get_project_root

# -----------------------------------------
# MODEL NAME (single source of truth)
# -----------------------------------------
MODEL_NAME = "xgboost".lower()


# =========================================
# MODEL PATHS
# =========================================
def get_model_dir(version: str) -> Path:
    """
    models/v1/xgboost/
    """
    root = get_project_root()
    return root / "models" / version / MODEL_NAME


def get_model_path(version: str) -> Path:
    """
    models/v1/xgboost/model_bundle.pkl
    """
    return get_model_dir(version) / "model_bundle.pkl"


# =========================================
# S3 PATHS
# =========================================
def get_model_s3_key(version: str) -> str:
    """
    v1/xgboost/model_bundle.pkl
    """
    return f"{version}/{MODEL_NAME}/model_bundle.pkl"
