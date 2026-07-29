import os
import uuid

import aiofiles
from fastapi import UploadFile

from app.core.config import settings

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "application/msword",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


async def save_resume(file: UploadFile) -> tuple[str, str]:
    original = file.filename or "upload"
    safe_name = os.path.basename(original).replace("\x00", "")
    if not safe_name:
        safe_name = "upload"

    try:
        from app.services.s3 import upload_resume
        s3_key = upload_resume(file)
        file_path = s3_key
    except (ImportError, RuntimeError):
        folder = f"resumes/{uuid.uuid4()}"
        full_dir = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(full_dir, exist_ok=True)

        file_path = os.path.join(folder, safe_name)
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)

        async with aiofiles.open(full_path, "wb") as f:
            content = await file.read()
            await f.write(content)

    return file_path, original
