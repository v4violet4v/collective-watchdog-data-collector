from __future__ import annotations

from pathlib import Path

import boto3

from config import CollectorConfig


def read_snapshots(config: CollectorConfig) -> dict:
    if not all([config.r2_bucket, config.r2_endpoint_url, config.r2_access_key_id, config.r2_secret_access_key]):
        return {}
    import json
    from botocore.exceptions import ClientError
    client = boto3.client("s3", endpoint_url=config.r2_endpoint_url,
                          aws_access_key_id=config.r2_access_key_id,
                          aws_secret_access_key=config.r2_secret_access_key, region_name="auto")
    try:
        result = client.get_object(Bucket=config.r2_bucket, Key="latest/probability-snapshots.json")
        return json.loads(result["Body"].read())
    except ClientError as exc:
        if exc.response["Error"]["Code"] in {"NoSuchKey", "404"}:
            return {}
        raise


def upload_directory_to_r2(config: CollectorConfig) -> None:
    if not all([config.r2_bucket, config.r2_endpoint_url, config.r2_access_key_id, config.r2_secret_access_key]):
        message = "R2 upload skipped: R2 environment variables are not fully configured."
        if config.require_r2_upload:
            raise RuntimeError(message)
        print(message)
        return

    json_files = sorted(config.output_dir.rglob("*.json"), key=lambda path: (
        path.relative_to(config.output_dir).as_posix() in {"latest/summary.json", "latest/probability-snapshots.json"},
        path.relative_to(config.output_dir).as_posix(),
    ))
    if not json_files:
        message = f"R2 upload skipped: no JSON files found under {config.output_dir}."
        if config.require_r2_upload:
            raise RuntimeError(message)
        print(message)
        return

    client = boto3.client(
        "s3",
        endpoint_url=config.r2_endpoint_url,
        aws_access_key_id=config.r2_access_key_id,
        aws_secret_access_key=config.r2_secret_access_key,
        region_name="auto",
    )

    uploaded = 0
    for path in json_files:
        key = path.relative_to(config.output_dir).as_posix()
        client.upload_file(
            str(path),
            config.r2_bucket,
            key,
            ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=60"},
        )
        uploaded += 1
        print(f"Uploaded r2://{config.r2_bucket}/{key}")

    print(f"Uploaded {uploaded} JSON files to R2 bucket {config.r2_bucket}.")
