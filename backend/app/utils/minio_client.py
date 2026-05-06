"""
MinIO On-Premises Object Store Client
======================================
Provides a singleton boto3 S3 client configured to talk to the campus-hosted
MinIO instance rather than any public cloud endpoint.

WHY MinIO + boto3?
  - boto3 supports any S3-compatible API via ``endpoint_url``.
  - MinIO runs inside the Docker backend network, never leaving the campus
    trust boundary — satisfying the paper's strict data-sovereignty mandate.
  - Raw classroom audio is stored ephemerally: objects are deleted by the
    Celery worker immediately after successful transcription.

Usage:
    from app.utils.minio_client import get_minio_client, ensure_bucket_exists

    client = get_minio_client()
    client.upload_fileobj(file_obj, BUCKET, object_key)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (resolved from environment variables at module load-time)
# ---------------------------------------------------------------------------

MINIO_ENDPOINT   = os.environ.get("MINIO_ENDPOINT",   "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET     = os.environ.get("MINIO_BUCKET_NAME", "scholarlab-audio")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_minio_client():
    """
    Return a cached boto3 S3 client pointed at the campus MinIO instance.

    ``path_style=True`` (``addressing_style='path'``) is required for MinIO —
    it does not support virtual-hosted-style bucket addressing.
    """
    client = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        # Disable SSL verification for HTTP-only local endpoints; enable in prod
        verify=MINIO_ENDPOINT.startswith("https"),
    )
    logger.info("MinIO client initialised (endpoint=%s)", MINIO_ENDPOINT)
    return client


def ensure_bucket_exists(bucket_name: str = MINIO_BUCKET) -> None:
    """
    Idempotent bucket provisioner — called once on application startup.

    Creates the bucket if it does not already exist. Safe to call multiple
    times (catches ``BucketAlreadyOwnedByYou`` and ``BucketAlreadyExists``).
    """
    client = get_minio_client()
    try:
        client.head_bucket(Bucket=bucket_name)
        logger.info("MinIO bucket '%s' already exists", bucket_name)
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        if error_code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket_name)
            logger.info("Created MinIO bucket '%s'", bucket_name)
        elif error_code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            logger.debug("MinIO bucket '%s' already owned", bucket_name)
        else:
            logger.error(
                "Unexpected MinIO error checking bucket '%s': %s", bucket_name, exc
            )
            raise
