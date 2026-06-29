"""AWS S3 service for resume storage."""
import logging
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger("ats.s3")

s3_client = None


def _get_s3_client():
    """Lazy initialization of S3 client."""
    global s3_client
    if s3_client is None:
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_REGION, settings.S3_BUCKET_NAME]):
            raise RuntimeError("AWS S3 configuration is incomplete. Check environment variables.")
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
    return s3_client


def upload_resume(file: UploadFile) -> str:
    """
    Upload resume file to S3.
    Returns s3_key (path within bucket).
    Key format: resumes/{uuid}/{original_filename}
    """
    client = _get_s3_client()
    s3_key = f"resumes/{uuid4()}/{file.filename}"

    client.upload_fileobj(
        file.file,
        settings.S3_BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )

    logger.info(f"Uploaded resume to S3: {s3_key}")
    return s3_key


def get_presigned_download_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """
    Generate a temporary presigned URL for secure resume download.
    URL expires after expiry_seconds (default 1 hour).
    """
    client = _get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": s3_key,
            "ResponseContentDisposition": "attachment",
        },
        ExpiresIn=expiry_seconds,
    )
    return url


def delete_resume(s3_key: str) -> None:
    """
    Delete resume file from S3.
    Treats deletion of non-existent key as success.
    """
    try:
        client = _get_s3_client()
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        logger.info(f"Deleted S3 object: {s3_key}")
    except ClientError as e:
        logger.error(f"Failed to delete S3 object {s3_key}: {e}")
