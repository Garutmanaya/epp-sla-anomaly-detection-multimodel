"""Common data contract metadata shared by the backend and dashboard."""

DATA_DICTIONARY = {
    "version": "1.0.0",
    "model_names": ["xgboost", "isolationforest"],
    "command_names": ["CHECK-DOMAIN", "ADD-DOMAIN", "MOD-DOMAIN", "DEL-DOMAIN"],
    "status_values": ["Normal ✅", "LOW ⚠️", "MEDIUM ⚠️", "CRITICAL 🚨"],
    "normal_status": "Normal ✅",
    "key_columns": ["timestamp", "command"],
    "required_input_columns": [
        "timestamp",
        "command",
        "success_vol",
        "success_rt_avg",
        "fail_vol",
        "fail_rt_avg",
    ],
    "generated_input_columns": [
        "timestamp",
        "command",
        "success_vol",
        "success_rt_avg",
        "fail_vol",
        "fail_rt_avg",
        "is_anomaly",
        "anomaly_type",
    ],
    "result_columns": [
        "Timestamp",
        "Command",
        "Hour",
        "Status",
        "Severity",
        "Root_Cause",
        "Actual",
        "Expected",
        "Deviation",
    ],
}

MODEL_OPTIONS = DATA_DICTIONARY["model_names"]
COMMAND_OPTIONS = DATA_DICTIONARY["command_names"]
STATUS_OPTIONS = DATA_DICTIONARY["status_values"]
NORMAL_STATUS = DATA_DICTIONARY["normal_status"]
KEY_COLUMNS = DATA_DICTIONARY["key_columns"]
REQUIRED_INPUT_COLUMNS = DATA_DICTIONARY["required_input_columns"]
GENERATED_INPUT_COLUMNS = DATA_DICTIONARY["generated_input_columns"]
RESULT_COLUMNS = DATA_DICTIONARY["result_columns"]
