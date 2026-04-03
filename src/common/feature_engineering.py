# =========================================
# MODULE: feature_engineering
# PURPOSE: Shared feature engineering for training & inference
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd
import numpy as np


# =========================================
# TIME FEATURES
# =========================================
def add_time_features(df):
    """
    Add cyclical hour features

    Args:
        df: input dataframe with 'timestamp'

    Returns:
        df with hour, hour_sin, hour_cos
    """

    df = df.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    return df


# =========================================
# COMMAND ENCODING
# =========================================
def encode_command(df, prefix="command_"):
    """
    One-hot encode command column

    Args:
        df: input dataframe
        prefix: prefix for columns

    Returns:
        df with encoded columns
    """

    df = df.copy()

    dummies = pd.get_dummies(df["command"], prefix="command")

    # rename to consistent format: command_ADD-DOMAIN
    dummies.columns = [f"{prefix}{c.replace('command_', '')}" for c in dummies.columns]

    df = pd.concat([df, dummies], axis=1)

    return df


# =========================================
# FEATURE PREPARATION (CORE ENTRY POINT)
# =========================================
def prepare_features(df):
    """
    Full feature pipeline

    Args:
        df: raw dataframe

    Returns:
        df with features
    """

    df = add_time_features(df)
    df = encode_command(df)

    return df


# =========================================
# FEATURE COLUMN EXTRACTION
# =========================================
def get_feature_columns(df, base_features, command_prefix="command_"):
    """
    Extract feature columns dynamically

    Args:
        df: dataframe
        base_features: list of base features
        command_prefix: prefix for command columns

    Returns:
        list of feature column names
    """

    command_cols = [
        c for c in df.columns
        if c.startswith(command_prefix) and c != "command"
    ]

    features = base_features + command_cols

    return features


# =========================================
# ALIGN FEATURES (CRITICAL FOR INFERENCE)
# =========================================
def align_features(df, feature_columns):
    """
    Ensure dataframe has all required feature columns

    Missing columns → filled with 0

    Args:
        df: input dataframe
        feature_columns: expected columns

    Returns:
        aligned dataframe
    """

    df = df.copy()

    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0

    return df[feature_columns]