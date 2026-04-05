# =========================================
# MODULE: s3_utils
# PURPOSE: S3 utilities (clean + consistent)
# =========================================

import os
import boto3

from common.config_loader import load_main_config, get_project_root
from common.path_utils import build_path

# =========================================
# CONFIG HELPERS
# =========================================
def get_s3_config():
    cfg = load_main_config()
    return cfg.get("s3", {})


def get_s3_bucket() -> str:
    bucket = get_s3_config().get("bucket")
    if not bucket:
        raise ValueError("Missing 's3.bucket' in config")
    return bucket


def get_s3_prefix() -> str:
    return get_s3_config().get("prefix", "").strip("/")


# =========================================
# CLIENT
# =========================================
def get_s3_client():
    return boto3.client("s3")


# =========================================
# KEY BUILDERS
# =========================================
def build_s3_key(relative_path: str) -> str:
    """
    Build S3 key using prefix + relative path
    """
    prefix = get_s3_prefix()

    if prefix:
        return f"{prefix}/{relative_path}".replace("\\", "/")
    return relative_path.replace("\\", "/")


def build_s3_key_from_local(local_path: str) -> str:
    """
    Convert local absolute path → S3 key
    """
    root = get_project_root()
    relative = os.path.relpath(local_path, root)
    return build_s3_key(relative)


# =========================================
# FILE OPERATIONS
# =========================================
def upload_file(local_path: str, s3_key: str = None):

    if not s3_key:
        s3_key = build_s3_key_from_local(local_path)

    s3 = get_s3_client()
    bucket = get_s3_bucket()

    s3.upload_file(local_path, bucket, s3_key)

    print(f"Uploaded → s3://{bucket}/{s3_key}")


def download_file(s3_key: str, local_path: str):

    s3 = get_s3_client()
    bucket = get_s3_bucket()

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    s3.download_file(bucket, s3_key, local_path)

    print(f"Downloaded ← s3://{bucket}/{s3_key}")


# =========================================
# VERSION-BASED DOWNLOAD
# =========================================
def download_models_for_version(version: str):
    """
    Download all models for given version:
    s3://bucket/prefix/models/{version}/...
    """

    s3 = get_s3_client()
    bucket = get_s3_bucket()

    prefix = build_s3_key(f"models/{version}/")

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    if "Contents" not in response:
        print(f"No models found: {prefix}")
        return

    root = get_project_root()

    for obj in response["Contents"]:

        key = obj["Key"]

        if key.endswith("/"):
            continue

        # Convert S3 key → local path
        relative = key.replace(get_s3_prefix() + "/", "", 1) if get_s3_prefix() else key
        local_path = os.path.join(root, relative)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if not os.path.exists(local_path):
            print(f"Downloading {key}")
            s3.download_file(bucket, key, local_path)

# =========================================
# S3 Path to Local Path
# =========================================
def s3_to_local_path(s3_key: str) -> str:

    root = get_project_root()
    prefix = get_s3_prefix()

    if prefix and s3_key.startswith(prefix):
        s3_key = s3_key[len(prefix) + 1:]

    return build_path(s3_key)            