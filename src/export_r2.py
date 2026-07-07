from __future__ import annotations

from pathlib import Path

import boto3

from config import CollectorConfig


def upload_directory_to_r2(config: CollectorConfig) -> None:
    if not all([config.r2_bucket, config.r2_endpoint_url, config.r2_access_key_id, config.r2_secret_access_key]):
        print("R2 upload skipped: R2 environment variables are not fully configured.")
        return

    client = boto3.client(
        "s3",
        endpoint_url=config.r2_endpoint_url,
        aws_access_key_id=config.r2_access_key_id,
        aws_secret_access_key=config.r2_secret_access_key,
        region_name="auto",
    )

    for path in config.output_dir.rglob("*.json"):
        key = path.relative_to(config.output_dir).as_posix()
        client.upload_file(
            str(path),
            config.r2_bucket,
            key,
            ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=60"},
        )
        print(f"Uploaded r2://{config.r2_bucket}/{key}")

