# =========================================
# MODULE: config
# PURPOSE: Central configuration (type-safe)
# =========================================

# =========================================
# IMPORTS
# =========================================
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict


# =========================================
# DATA CONFIG
# =========================================
@dataclass
class DataConfig:
    test_size: float = 0.2


# =========================================
# FEATURE CONFIG
# =========================================
@dataclass
class FeatureConfig:
    base_features: List[str] = field(
        default_factory=lambda: ["hour_sin", "hour_cos"]
    )
    command_prefix: str = "command_"


# =========================================
# MODEL CONFIG
# =========================================
@dataclass
class ModelConfig:
    targets: List[str] = field(
        default_factory=lambda: [
            "success_vol",
            "success_rt_avg",
            "fail_vol",
            "fail_rt_avg"
        ]
    )

    n_estimators: int = 200
    max_depth: int = 5
    learning_rate: float = 0.05
    random_state: int = 42


# =========================================
# THRESHOLD CONFIG
# =========================================
@dataclass
class ThresholdConfig:

    # Core logic
    percentile: float = 0.99

    # Alert tuning
    target_alert_rate: float = 0.01
    safety_factor: float = 1.2

    # Auto-tuning support
    factor_range: np.ndarray = field(
        default_factory=lambda: np.arange(1.0, 5.0, 0.1)
    )

    # Minimum absolute guard (stability)
    min_absolute: Dict[str, float] = field(
        default_factory=lambda: {
            "fail_vol": 500,
            "success_vol": 500,
            "fail_rt_avg": 0.5,
            "success_rt_avg": 0.5
        }
    )

    # Minimum threshold floor (avoid over-sensitivity)
    min_floor: Dict[str, float] = field(
        default_factory=lambda: {
            "fail_vol": 0.05,
            "success_vol": 0.05,
            "fail_rt_avg": 0.05,
            "success_rt_avg": 0.05
        }
    )


# =========================================
# GLOBAL CONFIG
# =========================================
@dataclass
class Config:
    version: str
    data: DataConfig
    features: FeatureConfig
    model: ModelConfig
    threshold: ThresholdConfig


# =========================================
# FACTORY FUNCTION
# =========================================
def load_config(version: str) -> Config:
    """
    Build config object for given version
    """

    return Config(
        version=version,
        data=DataConfig(),
        features=FeatureConfig(),
        model=ModelConfig(),
        threshold=ThresholdConfig()
    )
