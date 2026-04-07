# =========================================
# MODULE: train
# PURPOSE: Train XGBoost models with MLflow tracking
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd
import mlflow
import mlflow.xgboost

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor


from common.config import load_config
from common.config_loader import (
    resolve_version_path,
    get_data_filename,
    get_active_version,
    get_flag,
)
from common.feature_engineering import (
    prepare_features,
    get_feature_columns
)
from common.mlflow_utils import configure_mlflow
from xgboost_ad.local_utils import get_model_s3_key, save_model_bundle
from common.s3_utils import upload_file

# =========================================
# LOAD DATA
# =========================================
def load_training_data(cfg):

    filename = get_data_filename()

    path = resolve_version_path(
        base_dir="data",
        filename=filename,
        version=cfg.version
    )

    return pd.read_csv(path)


# =========================================
# TRAIN MODEL
# =========================================
def train_model(X_train, y_train, X_val, y_val, cfg):

    model = XGBRegressor(
        n_estimators=cfg.model.n_estimators,
        max_depth=cfg.model.max_depth,
        learning_rate=cfg.model.learning_rate,
        random_state=cfg.model.random_state,
        eval_metric="mae"
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=True   # prints boosting rounds
    )

    return model


# =========================================
# TRAIN ALL TARGETS
# =========================================
def train_all_models(df, cfg):

    df = prepare_features(df)

    FEATURES = get_feature_columns(
        df,
        base_features=cfg.features.base_features,
        command_prefix=cfg.features.command_prefix
    )

    X = df[FEATURES]

    models = {}
    metrics = {}

    for target in cfg.model.targets:

        y = df[target]

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=cfg.data.test_size, random_state=42
        )

        model = train_model(X_train, y_train, X_val, y_val, cfg)

        preds = model.predict(X_val)
        mae = mean_absolute_error(y_val, preds)

        models[target] = model
        metrics[target] = mae

        print(f"{target} MAE: {mae:.4f}")
        mlflow.log_metric(f"{target}_mae", mae)

    return models, FEATURES


# =========================================
# SAVE MODEL
# =========================================
def save_model(models, FEATURES, cfg):

    bundle = {
        "models": models,
        "features": FEATURES,
        "targets": cfg.model.targets,
        "version": cfg.version
    }

    model_path = save_model_bundle(bundle, cfg.version)

    print(f"Model saved: {model_path}")
    mlflow.log_artifact(model_path)

    # ✅ Upload to S3
    if get_flag("upload_to_s3"):
        s3_key = get_model_s3_key(cfg.version)

        upload_file(str(model_path), s3_key)

# =========================================
# MAIN
# =========================================
def main():

    version = get_active_version()
    cfg = load_config(version)

    # MLflow setup
    configure_mlflow()

    with mlflow.start_run(run_name=f"train_{cfg.version}"):

        mlflow.log_param("version", cfg.version)
        mlflow.log_params({
            "n_estimators": cfg.model.n_estimators,
            "max_depth": cfg.model.max_depth,
            "learning_rate": cfg.model.learning_rate
        })

        df = load_training_data(cfg)

        models, FEATURES = train_all_models(df, cfg)

        save_model(models, FEATURES, cfg)

        print("Training complete")


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    main()
