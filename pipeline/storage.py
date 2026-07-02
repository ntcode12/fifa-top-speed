"""Thin S3 helpers for the FIFA top-speed pipeline."""

import os

import boto3
from botocore.exceptions import ClientError

DEFAULT_BUCKET = "fifa-topspeed-032968994565"


def bucket_name() -> str:
    return os.environ.get("FIFA_BUCKET", DEFAULT_BUCKET)


def _client():
    return boto3.client("s3")


def object_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_bytes(key: str, data: bytes) -> None:
    _client().put_object(Bucket=bucket_name(), Key=key, Body=data)


def download_bytes(key: str) -> bytes:
    return _client().get_object(Bucket=bucket_name(), Key=key)["Body"].read()


def list_keys(prefix: str) -> list[str]:
    paginator = _client().get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket_name(), Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys
