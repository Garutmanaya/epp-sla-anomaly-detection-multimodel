# =========================================
# MODULE: s3_utils
# PURPOSE: Upload/download files to S3
# =========================================

# =========================================
# IMPORTS
# =========================================
import boto3
import os

from common.config_loader import load_main_config , get_project_root


# =========================================
# CLIENT
# =========================================
def get_s3_client():
    return boto3.client("s3")


# =========================================
# GET S3 CONFIG
# =========================================
def get_s3_config():
    config = load_main_config()
    return config.get("s3", {})


# =========================================
# UPLOAD FILE
# =========================================
def upload_file(local_path, s3_key):
    """
    Upload file to S3

    Args:
        local_path: local file path
        s3_key: S3 object key
    """

    s3 = get_s3_client()
    s3_config = get_s3_config()

    bucket = s3_config.get("bucket")

    if not bucket:
        raise ValueError("S3 bucket not defined in config")

    s3.upload_file(local_path, bucket, s3_key)

    print(f"Uploaded to s3://{bucket}/{s3_key}")

# =========================================
# DOWNLOAD FILE
# =========================================
def download_file(s3_key, local_path):
    """
    Download file from S3
    """

    s3 = get_s3_client()
    s3_config = get_s3_config()

    bucket = s3_config.get("bucket")

    if not bucket:
        raise ValueError("S3 bucket not defined")

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    s3.download_file(bucket, s3_key, local_path)

    print(f"Downloaded from s3://{bucket}/{s3_key} → {local_path}") 

# =========================================
# BUILD S3 KEY 
# =========================================
def build_s3_key(local_path):
    """
    Convert absolute path → relative project path → S3 key
    """

    s3_config = get_s3_config()
    prefix = s3_config.get("prefix", "")

    root = get_project_root()

    relative_path = os.path.relpath(local_path, root)

    return f"{prefix}/{relative_path}"

