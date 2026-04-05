# =========================================
# MODULE: config_loader
# PURPOSE: Centralized config + root-safe path resolution
# =========================================

import json
import os
from pathlib import Path


# =========================================
# ROOT RESOLUTION
# =========================================
def get_project_root() -> Path:
    """
    Robust project root detection using pyproject.toml
    """
    path = Path(__file__).resolve()

    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("Could not locate project root (pyproject.toml missing)")


# =========================================
# PATH RESOLUTION
# =========================================
def resolve_path(relative_path: str) -> str:
    """
    Convert relative path → absolute path using project root
    """
    return str(get_project_root() / relative_path)


# =========================================
# LOAD MAIN CONFIG
# =========================================
def load_main_config(config_path: str = None) -> dict:
    """
    Load main.config.json from project root
    """
    if config_path is None:
        config_path = resolve_path("configs/main.config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Main config not found: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


# =========================================
# VERSION
# =========================================
def get_active_version(config: dict = None) -> str:
    if config is None:
        config = load_main_config()

    return config.get("active_version", "v1")


# =========================================
# GENERIC CONFIG ACCESS
# =========================================
def get_section(section: str, config: dict = None) -> dict:
    if config is None:
        config = load_main_config()

    return config.get(section, {})


# =========================================
# PATHS (from config.paths)
# =========================================
def get_paths(config=None) -> dict:
    raw_paths = get_section("paths", config)

    return {
        key: resolve_path(path)
        for key, path in raw_paths.items()
    }


def get_path(key: str, config=None) -> str:
    paths = get_paths(config)

    if key not in paths:
        raise KeyError(f"Path '{key}' not found in config")

    return paths[key]


# =========================================
# VERSIONED PATH (legacy support)
# =========================================
def resolve_version_path(base_dir: str, filename: str, version: str = None) -> str:
    """
    Build:
    project_root/base_dir/version/filename
    """
    if version is None:
        version = get_active_version()

    return resolve_path(os.path.join(base_dir, version, filename))


# =========================================
# DATA CONFIG
# =========================================
def load_data_config(config=None) -> dict:
    try:
        path = get_path("data_config", config)
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def get_data_settings(config=None) -> dict:
    return get_section("data", config)


def get_data_filename(config=None) -> str:
    return get_data_settings(config).get("filename", "data.csv")


# =========================================
# FLAGS
# =========================================
def get_flags(config=None) -> dict:
    return get_section("flags", config)


def get_flag(name: str, default=False, config=None):
    return get_flags(config).get(name, default)


# =========================================
# API / SAGEMAKER / S3 CONFIG
# =========================================
def get_api_config(config=None) -> dict:
    return get_section("api", config)


def get_sagemaker_config(config=None) -> dict:
    return get_section("sagemaker", config)


def is_sagemaker(config=None) -> bool:
    return get_sagemaker_config(config).get("enabled", False)


def get_s3_config(config=None) -> dict:
    return get_section("s3", config)