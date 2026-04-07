from datetime import datetime

from common.s3_utils import build_s3_key, upload_file
from common.config_loader import (
    resolve_version_path,
    get_flag,
    get_data_filename,
)
from shared.demo_data import (
    generate_baseline_data,
    load_generator_config as load_shared_generator_config,
)


def load_generator_config():
    return load_shared_generator_config()


def generate_data(start_date, hours, config):
    return generate_baseline_data(start_date=start_date, hours=hours, config=config)

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
