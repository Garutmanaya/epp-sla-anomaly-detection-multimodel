import os

import mlflow
from mlflow.tracking import MlflowClient

from common.config_loader import get_project_root

DEFAULT_EXPERIMENT_NAME = "anomaly-detection"


def get_mlflow_tracking_uri() -> str:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        return tracking_uri

    db_path = get_project_root() / "mlflow.db"
    return f"sqlite:///{db_path}"


def get_mlflow_registry_uri() -> str:
    return os.getenv("MLFLOW_REGISTRY_URI", get_mlflow_tracking_uri())


def get_mlflow_artifact_root() -> str:
    artifact_root = os.getenv("MLFLOW_ARTIFACT_ROOT")
    if artifact_root:
        return artifact_root

    artifact_path = get_project_root() / "mlartifacts"
    artifact_path.mkdir(parents=True, exist_ok=True)
    return artifact_path.resolve().as_uri()


def configure_mlflow(experiment_name: str = DEFAULT_EXPERIMENT_NAME) -> str:
    tracking_uri = get_mlflow_tracking_uri()
    registry_uri = get_mlflow_registry_uri()

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(registry_uri)

    client = MlflowClient(tracking_uri=tracking_uri, registry_uri=registry_uri)
    experiment = client.get_experiment_by_name(experiment_name)

    if experiment is None:
        artifact_root = get_mlflow_artifact_root()
        client.create_experiment(experiment_name, artifact_location=artifact_root)

    mlflow.set_experiment(experiment_name)
    return tracking_uri
