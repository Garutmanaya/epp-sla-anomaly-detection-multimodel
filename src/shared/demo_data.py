"""Shared synthetic demo-data helpers for the backend and dashboard."""

from copy import deepcopy
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from shared.generator_config import GENERATOR_CONFIG

np.random.seed(42)


def load_generator_config() -> dict:
    return deepcopy(GENERATOR_CONFIG)


def add_noise(value: float, pct: float) -> float:
    return value * (1 + np.random.uniform(-pct, pct))


def random_in_range(low: float, high: float, pct: float) -> float:
    return add_noise(np.random.uniform(low, high), pct)


def apply_hourly_rules(cmd: str, hour: int, values: dict, hourly_rules: dict) -> dict:
    rules = hourly_rules.get(str(hour), {}).get(cmd, {})

    for key, multiplier in rules.items():
        field = key.replace("_multiplier", "")
        if field in values:
            values[field] *= multiplier

    return values


def inject_anomaly(values: dict) -> tuple[dict, str]:
    metric = np.random.choice(["success_vol", "fail_vol", "success_rt", "fail_rt"])
    direction = np.random.choice(["up", "down"])
    factor = np.random.uniform(3, 10) if direction == "up" else np.random.uniform(0.1, 0.5)
    values[metric] *= factor
    return values, f"{metric}_{direction}"


def _normalize_start_date(start_date):
    if isinstance(start_date, str):
        return datetime.fromisoformat(start_date)
    return start_date


def generate_baseline_data(start_date, hours: int, config: dict | None = None) -> pd.DataFrame:
    config = deepcopy(config) if config is not None else load_generator_config()
    start_date = _normalize_start_date(start_date)

    randomness = config["randomness"]
    commands_config = config["commands"]
    hourly_rules = config["hourly_rules"]

    data = []
    current = start_date

    for _ in range(hours):
        hour = current.hour

        for cmd, cfg in commands_config.items():
            values = {
                "success_vol": add_noise(cfg["success_vol"], randomness),
                "fail_vol": add_noise(cfg["fail_vol"], randomness),
                "success_rt": random_in_range(*cfg["success_rt"], randomness),
                "fail_rt": random_in_range(*cfg["fail_rt"], randomness),
            }

            values = apply_hourly_rules(cmd, hour, values, hourly_rules)

            data.append(
                {
                    "timestamp": current,
                    "command": cmd,
                    "success_vol": int(values["success_vol"]),
                    "success_rt_avg": round(values["success_rt"], 3),
                    "fail_vol": int(values["fail_vol"]),
                    "fail_rt_avg": round(values["fail_rt"], 3),
                }
            )

        current += timedelta(hours=1)

    return pd.DataFrame(data)


def generate_test_data(
    start_date,
    hours: int,
    anomaly_prob: float = 0.2,
    config: dict | None = None,
) -> pd.DataFrame:
    config = deepcopy(config) if config is not None else load_generator_config()
    start_date = _normalize_start_date(start_date)

    randomness = config["randomness"]
    commands_config = config["commands"]
    hourly_rules = config["hourly_rules"]

    data = []
    current = start_date

    for _ in range(hours):
        hour = current.hour

        for cmd, cfg in commands_config.items():
            values = {
                "success_vol": add_noise(cfg["success_vol"], randomness),
                "fail_vol": add_noise(cfg["fail_vol"], randomness),
                "success_rt": random_in_range(*cfg["success_rt"], randomness),
                "fail_rt": random_in_range(*cfg["fail_rt"], randomness),
            }

            values = apply_hourly_rules(cmd, hour, values, hourly_rules)
            is_anomaly = False
            anomaly_type = "normal"

            if np.random.rand() < anomaly_prob:
                values, anomaly_type = inject_anomaly(values)
                is_anomaly = True

            data.append(
                {
                    "timestamp": current,
                    "command": cmd,
                    "success_vol": int(values["success_vol"]),
                    "success_rt_avg": round(values["success_rt"], 3),
                    "fail_vol": int(values["fail_vol"]),
                    "fail_rt_avg": round(values["fail_rt"], 3),
                    "is_anomaly": is_anomaly,
                    "anomaly_type": anomaly_type,
                }
            )

        current += timedelta(hours=1)

    return pd.DataFrame(data)
