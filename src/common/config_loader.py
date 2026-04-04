# =========================================
# MODULE: config_loader
# PURPOSE: Centralized config + path resolution (root-safe)
# =========================================

# =========================================
# IMPORTS
# =========================================
import json
import os
from pathlib import Path


# =========================================
# ROOT RESOLUTION
# =========================================
def get_project_root():
    """
    Robust project root detection using pyproject.toml
    """
    path = Path(__file__).resolve()

    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("Could not locate project root")

def resolve_path(relative_path):
    """
    Convert relative path → absolute path using project root
    """
    root = get_project_root()
    return os.path.join(root, relative_path)


# =========================================
# LOAD MAIN CONFIG
# =========================================
def load_main_config(config_path=None):
    """
    Load main config from project root
    """
    if config_path is None:
        config_path = resolve_path("configs/main.config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Main config not found: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


# =========================================
# GET ACTIVE VERSION
# =========================================
def get_active_version(config=None):
    if config is None:
        config = load_main_config()

    return config.get("active_version", "v1")


# =========================================
# GET PATHS (ROOT-RESOLVED)
# =========================================
def get_paths(config=None):
    """
    Returns all paths resolved to absolute paths
    """
    if config is None:
        config = load_main_config()

    raw_paths = config.get("paths", {})

    resolved = {}
    for key, path in raw_paths.items():
        resolved[key] = resolve_path(path)

    return resolved


# =========================================
# GET SPECIFIC PATH (ROOT-RESOLVED)
# =========================================
def get_path(key, config=None):
    paths = get_paths(config)

    if key not in paths:
        raise KeyError(f"Path '{key}' not found in config")

    return paths[key]


# =========================================
# RESOLVE VERSIONED PATH (ROOT-RESOLVED)
# =========================================
def resolve_version_path(base_dir, filename, version=None):
    """
    Build absolute path:
        project_root/base_dir/version/file
    """
    if version is None:
        version = get_active_version()

    relative = os.path.join(base_dir, version, filename)
    return resolve_path(relative)


# =========================================
# LOAD DATA CONFIG (ROOT-RESOLVED)
# =========================================
def load_data_config(config=None):
    try:
        path = get_path("data_config", config)
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {} 
    
# =========================================
# GET FLAGS
# =========================================
def get_flags(config=None):
    if config is None:
        config = load_main_config()

    return config.get("flags", {})


def get_flag(name, default=False, config=None):
    flags = get_flags(config)
    return flags.get(name, default) 

# =========================================
# GET DATA CONFIG (FROM main.config.json)
# =========================================
def get_data_settings(config=None):
    if config is None:
        config = load_main_config()

    return config.get("data", {})


def get_data_filename(config=None):
    data_cfg = get_data_settings(config)
    return data_cfg.get("filename", "data.csv")  # safe default 

# =========================================
# GET API and SAGEMAKER CONFIG (FROM main.config.json)
# =========================================
def get_api_config(config=None):
    if config is None:
        config = load_main_config()
    return config.get("api", {})

def get_sagemaker_config(config=None):
    if config is None:
        config = load_main_config()
    return config.get("sagemaker", {}) 

def is_sagemaker():
    if config is None:
        config = load_main_config()
    return config.get("sagemaker", {}).get("enabled", False)