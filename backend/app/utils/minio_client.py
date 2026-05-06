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

import io
import logging
import os
import shutil
from functools import lru_cache
from pathlib import Path

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
# Local Mock Client (for development without MinIO)
# ---------------------------------------------------------------------------

class MockMinioClient:
    """
    A minimal mock of the boto3 S3 client that uses the local filesystem.
    Enabled automatically in 'dev' environment if MinIO is unreachable.
    """
    def __init__(self, base_dir: str = "data/minio_mock"):
        # Use absolute path to ensure Celery workers can find it
        self.base_dir = os.path.abspath(os.path.join(os.getcwd(), base_dir))
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info("Using MockMinioClient (local filesystem) at %s", self.base_dir)

    def upload_fileobj(self, Fileobj, Bucket, Key, ExtraArgs=None):
        path = os.path.join(self.base_dir, Bucket, Key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Reset pointer just in case
        try:
            Fileobj.seek(0)
        except (AttributeError, io.UnsupportedOperation):
            pass

        with open(path, "wb") as f:
            shutil.copyfileobj(Fileobj, f)
        logger.info("MockMinio: Uploaded %s/%s to %s", Bucket, Key, path)

    def download_fileobj(self, Bucket, Key, Fileobj):
        path = os.path.join(self.base_dir, Bucket, Key)
        if not os.path.exists(path):
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}}, 
                "download_fileobj"
            )
        
        with open(path, "rb") as f:
            shutil.copyfileobj(f, Fileobj)
        logger.info("MockMinio: Downloaded %s/%s from %s", Bucket, Key, path)

    def head_object(self, Bucket, Key):
        path = os.path.join(self.base_dir, Bucket, Key)
        if os.path.exists(path):
            return {"ContentLength": os.path.getsize(path)}
        raise ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, 
            "head_object"
        )

    def delete_object(self, Bucket, Key):
        path = os.path.join(self.base_dir, Bucket, Key)
        if os.path.exists(path):
            os.remove(path)
            logger.info("MockMinio: Deleted %s/%s", Bucket, Key)
            return {"ResponseMetadata": {"HTTPStatusCode": 204}}
        raise ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, 
            "delete_object"
        )

    def create_bucket(self, Bucket):
        os.makedirs(os.path.join(self.base_dir, Bucket), exist_ok=True)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def head_bucket(self, Bucket):
        if os.path.exists(os.path.join(self.base_dir, Bucket)):
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        raise ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, 
            "head_bucket"
        )


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_minio_client():
    """
    Return a cached boto3 S3 client pointed at the campus MinIO instance.
    
    If in 'dev' environment and MinIO is unreachable, falls back to a 
    filesystem-backed MockMinioClient to prevent breaking the upload flow.
    """
    # Check if we should use the mock (only in dev)
    env = os.environ.get("SCHOLARLAB_ENV", "dev")
    
    use_mock = False
    if env == "dev":
        # Check if MinIO is actually reachable
        import socket
        try:
            # Extract host and port from endpoint
            # e.g. http://localhost:9000 -> localhost, 9000
            parts = MINIO_ENDPOINT.replace("http://", "").replace("https://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else (80 if "https" not in MINIO_ENDPOINT else 443)
            
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except (socket.timeout, ConnectionRefusedError, socket.gaierror, IndexError):
            logger.warning(
                "MinIO endpoint %s unreachable. Falling back to local filesystem "
                "mock for development.", MINIO_ENDPOINT
            )
            use_mock = True

    if use_mock:
        return MockMinioClient()

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
    try:
        client = get_minio_client()
        client.head_bucket(Bucket=bucket_name)
        logger.info("MinIO bucket '%s' already exists", bucket_name)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        if error_code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket_name)
            logger.info("Created MinIO bucket '%s'", bucket_name)
        elif error_code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            logger.debug("MinIO bucket '%s' already owned", bucket_name)
        else:
            logger.error(
                "Unexpected MinIO error checking bucket '%s': %s", bucket_name, exc
            )
            # Don't raise in dev if we are using the mock or if it's a transient error
            if os.environ.get("SCHOLARLAB_ENV") != "dev":
                raise
    except Exception as e:
        logger.error("Failed to ensure MinIO bucket exists: %s", e)
        if os.environ.get("SCHOLARLAB_ENV") != "dev":
            raise
