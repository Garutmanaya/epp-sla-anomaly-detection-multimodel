# =========================================
# MODULE: model_registry
# =========================================

def get_model_runner(model_name: str):

    if model_name == "xgboost":
        from xgboost_ad.inference import run_inference
        return run_inference

    elif model_name == "isolationforest":
        from isolationforest_ad.inference import run_inference
        return run_inference

    else:
        raise ValueError(f"Unsupported model: {model_name}")
