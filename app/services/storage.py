import logging
import os
import uuid

import aiofiles
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger("ats.storage")

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "application/msword",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def is_s3_configured() -> bool:
    """Whether AWS S3 is configured as the resume storage backend."""
    return bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY
        and settings.S3_BUCKET_NAME
    )


async def save_resume(file: UploadFile) -> tuple[str, str]:
    original = file.filename or "upload"
    safe_name = os.path.basename(original).replace("\x00", "")
    if not safe_name:
        safe_name = "upload"

    if is_s3_configured():
        from app.services.s3 import upload_resume
        file_path = upload_resume(file)
    else:
        folder = f"resumes/{uuid.uuid4()}"
        full_dir = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(full_dir, exist_ok=True)

        file_path = os.path.join(folder, safe_name)
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)

        async with aiofiles.open(full_path, "wb") as f:
            content = await file.read()
            await f.write(content)

    return file_path, original


def local_resume_path(file_path: str) -> str:
    return os.path.join(settings.UPLOAD_DIR, file_path)


def delete_local_resume(file_path: str) -> None:
    """Delete a locally stored resume. Missing files are treated as already deleted."""
    full_path = local_resume_path(file_path)
    try:
        os.remove(full_path)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.error(f"Failed to delete local resume {file_path}: {e}")
