from common.model_utils import ModelUtils
import joblib

MODEL_NAME = "xgboost"

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


def load_model_bundle(version=None):
    model_path = get_model_path(version)
    return joblib.load(model_path)


def save_model_bundle(bundle, version=None):
    model_path = get_model_path(version)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    return model_path
