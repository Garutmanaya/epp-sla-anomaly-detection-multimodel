# =========================================
# MODULE: generate_data
# PURPOSE: Generate synthetic EPP data using config-driven rules
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from common.s3_utils import build_s3_key, upload_file
from common.config_loader import (
    get_path,
    resolve_version_path,
    load_main_config,
    get_flag,
    get_data_filename,
)


# =========================================
# CONFIG
# =========================================
np.random.seed(42)


# =========================================
# LOAD CONFIG
# =========================================
def load_generator_config():
    main_config = load_main_config()
    data_config_path = get_path("data_config", main_config)

    with open(data_config_path, "r") as f:
        config = json.load(f)

    return config


# =========================================
# HELPERS
# =========================================
def add_noise(value, pct):
    return value * (1 + np.random.uniform(-pct, pct))


def random_in_range(low, high, pct):
    base = np.random.uniform(low, high)
    return add_noise(base, pct)


def apply_hourly_rules(cmd, hour, values, hourly_rules):

    hour_str = str(hour)

    if hour_str in hourly_rules and cmd in hourly_rules[hour_str]:
        rules = hourly_rules[hour_str][cmd]

        for key, multiplier in rules.items():
            field = key.replace("_multiplier", "")
            if field in values:
                values[field] *= multiplier

    return values


# =========================================
# CORE LOGIC
# =========================================
def generate_data(start_date, hours, config):

    RANDOMNESS = config["randomness"]
    commands_config = config["commands"]
    hourly_rules = config["hourly_rules"]

    data = []
    current = start_date

    for _ in range(hours):
        hour = current.hour

        for cmd, cfg in commands_config.items():

            values = {
                "success_vol": add_noise(cfg["success_vol"], RANDOMNESS),
                "fail_vol": add_noise(cfg["fail_vol"], RANDOMNESS),
                "success_rt": random_in_range(*cfg["success_rt"], RANDOMNESS),
                "fail_rt": random_in_range(*cfg["fail_rt"], RANDOMNESS)
            }

            values = apply_hourly_rules(cmd, hour, values, hourly_rules)

            data.append({
                "timestamp": current,
                "command": cmd,
                "success_vol": int(values["success_vol"]),
                "success_rt_avg": round(values["success_rt"], 3),
                "fail_vol": int(values["fail_vol"]),
                "fail_rt_avg": round(values["fail_rt"], 3)
            })

        current += timedelta(hours=1)

    return pd.DataFrame(data)

# =========================================
# SAVE DATA to LOCAL DIRECTORY ( S3 )
# =========================================
def save_data(df):

    filename = get_data_filename()

    output_path = resolve_version_path(
        base_dir="data",
        filename=filename
    )

    df.to_csv(output_path, index=False)
    print(f"Data saved to: {output_path}")

    if get_flag("upload_to_s3"):
        s3_key = build_s3_key(output_path)
        upload_file(output_path, s3_key)


# =========================================
# MAIN
# =========================================
def main():

    config = load_generator_config()

    df = generate_data(
        start_date=datetime(2025, 1, 1),
        hours=24 * 90,
        config=config
    )

    save_data(df)

    print(df.head())


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    main()
