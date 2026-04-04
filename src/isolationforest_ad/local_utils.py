# =========================================
# MODULE: local_utils (Isolation Forest)
# =========================================

from pathlib import Path
from common.config_loader import get_project_root

MODEL_NAME = "isolationforest"

def get_model_dir(version: str):
    return get_project_root() / "models" / version / MODEL_NAME

def get_model_path(version: str):
    return get_model_dir(version) / "model_bundle.pkl"

def get_model_s3_key(version: str):
    return f"{version}/{MODEL_NAME}/model_bundle.pkl"