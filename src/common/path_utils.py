# =========================================
# MODULE: path_utils
# PURPOSE: Unified path builder (data, models, thresholds)
# =========================================

import os
from common.config_loader import get_project_root, get_active_version


# =========================================
# BASE HELPERS
# =========================================
def build_path(*parts) -> str:
    """
    Build absolute path from project root
    """
    return os.path.join(get_project_root(), *parts)


def build_version_path(base_dir: str, version: str, *parts) -> str:
    """
    Build version-based path
    """
    return build_path(base_dir, version, *parts)


# =========================================
# MODEL PATHS
# =========================================
def get_model_path(model_name: str, version: str = None) -> str:

    if version is None:
        version = get_active_version()

    return build_version_path(
        "models",
        version,
        model_name,
        "model_bundle.pkl"
    )


# =========================================
# DATA PATHS
# =========================================
def get_data_path(filename: str, version: str = None) -> str:

    if version is None:
        version = get_active_version()

    return build_version_path(
        "data",
        version,
        filename
    )


# =========================================
# CONFIG PATHS
# =========================================
def get_config_path(filename: str, version: str = None) -> str:

    if version is None:
        version = get_active_version()

    return build_version_path(
        "configs",
        version,
        filename
    )


# =========================================
# SPECIFIC HELPERS (CONVENIENCE)
# =========================================
def get_threshold_config_path(version: str = None) -> str:
    return get_config_path("threshold-config.json", version)


def get_data_config_path(version: str = None) -> str:
    return get_config_path("data-config.json", version)


def get_model_config_path(version: str = None) -> str:
    return get_config_path("model-config.json", version)