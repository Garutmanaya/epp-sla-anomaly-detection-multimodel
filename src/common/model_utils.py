# =========================================
# MODULE: model_utils
# PURPOSE: Generic model path + S3 utilities
# =========================================

from pathlib import Path

from common.config_loader import get_active_version
from common.path_utils import get_model_path as _get_model_path
from common.s3_utils import build_s3_key


class ModelUtils:
    """
    Generic utility for model-specific paths
    """

    def __init__(self, model_name: str):
        self.model_name = model_name.lower()

    # =========================================
    # LOCAL PATHS
    # =========================================
    def get_model_file_path(self, version: str = None) -> Path:
        if version is None:
            version = get_active_version()

        return Path(_get_model_path(self.model_name, version))

    def get_model_dir(self, version: str = None) -> Path:
        return self.get_model_file_path(version).parent

    # =========================================
    # S3 PATHS
    # =========================================
    def get_model_s3_key(self, version: str = None) -> str:
        if version is None:
            version = get_active_version()

        relative = f"models/{version}/{self.model_name}/model_bundle.pkl"
        return build_s3_key(relative)
