from common.model_utils import ModelUtils

MODEL_NAME = "isolationforest"

utils = ModelUtils(MODEL_NAME)


def get_model_file_path(version=None):
    return utils.get_model_file_path(version)


def get_model_dir(version=None):
    return utils.get_model_dir(version)


def get_model_s3_key(version=None):
    return utils.get_model_s3_key(version)

# =========================================
# BACKWARD COMPATIBILITY
# =========================================
def get_model_path(version=None):
    """
    Backward compatible alias
    """
    return get_model_file_path(version)