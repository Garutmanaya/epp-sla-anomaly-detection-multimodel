# =========================================
# MODULE: model_registry
# =========================================

MODEL_REGISTRY = {}


def register_model(model_name: str, engine):
    MODEL_REGISTRY[model_name] = engine


def get_model(model_name: str):
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Model not loaded: {model_name}")
    return MODEL_REGISTRY[model_name]


def is_model_loaded(model_name: str):
    return model_name in MODEL_REGISTRY