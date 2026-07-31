"""
One-time script to migrate locally stored resumes to S3.
Run once: python scripts/migrate_resumes_to_s3.py

What it does:
1. Fetches all documents rows from DB
2. For each document, reads file from local disk using current file_path
3. Uploads file to S3
4. Updates document.file_path with new S3 key
5. Logs success and failures

Run from project root with:
    docker compose exec api python scripts/migrate_resumes_to_s3.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session
from app.models.document import Document
from app.services.s3 import _get_s3_client
from app.core.config import settings

LOCAL_RESUME_DIR = Path("uploads")


async def migrate():
    client = _get_s3_client()

    async with async_session() as db:
        result = await db.execute(select(Document))
        documents = result.scalars().all()

        total = len(documents)
        success = 0
        failed = 0
        skipped = 0

        for doc in documents:
            local_path = LOCAL_RESUME_DIR / doc.file_path

            # Local and S3 storage both use a "resumes/<uuid>/<filename>" path shape,
            # so the only reliable idempotency check is whether a local file remains
            # to migrate. Once migrated, the DB row points at an S3 key, but the local
            # file itself is left in place, so this check re-uploads on re-run rather
            # than silently skipping — safe (same key gets overwritten) but not free.
            if not local_path.exists():
                print(f"SKIP — no local file, already migrated or missing: {local_path} (doc id: {doc.id})")
                skipped += 1
                continue

            try:
                new_s3_key = f"resumes/{doc.id}/{doc.original_filename}"
                with open(local_path, "rb") as f:
                    client.upload_fileobj(
                        f,
                        settings.S3_BUCKET_NAME,
                        new_s3_key,
                        ExtraArgs={"ContentType": "application/pdf"},
                    )

                doc.file_path = new_s3_key
                await db.commit()

                print(f"OK — migrated: {doc.original_filename} → {new_s3_key}")
                success += 1

            except Exception as e:
                await db.rollback()
                print(f"FAIL — {doc.original_filename} (doc id: {doc.id}): {e}")
                failed += 1

        print(f"\n{'='*50}")
        print(f"Migration complete.")
        print(f"  Total evaluated: {total}")
        print(f"  Already migrated (skipped): {skipped}")
        print(f"  Successful: {success}")
        print(f"  Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(migrate())
