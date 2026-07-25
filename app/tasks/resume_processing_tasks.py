import asyncio
import os
import uuid
from datetime import datetime, timezone

import structlog
from app.core.celery_app import celery_app
from app.core.config import settings
from app.database import async_session
from app.models.document import Document
from app.models.job import Job
from app.services.llm_extraction import extract_text_from_pdf, extract_resume_data
from app.services.embeddings import generate_embedding

log = structlog.get_logger("ats.tasks")


async def _process_resume_async(document_id: str):
    async with async_session() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if not document:
            log.error("document.not_found", document_id=document_id)
            return

        try:
            full_path = os.path.join(settings.UPLOAD_DIR, document.file_path)
            with open(full_path, "rb") as f:
                file_bytes = f.read()

            text = extract_text_from_pdf(file_bytes)
            if not text.strip():
                log.warn("document.empty_text", document_id=document_id)
                return

            extraction = await extract_resume_data(text)

            embedding_text = " ".join(extraction.skills) + " " + " ".join(
                wh.role + " " + wh.company for wh in extraction.work_history
            )
            embedding = await generate_embedding(embedding_text)

            document.parsed_data = extraction.model_dump()
            document.embedding = embedding
            document.parsed_at = datetime.now(timezone.utc)
            await db.commit()

            log.info("document.processed", document_id=document_id)

        except Exception as e:
            log.error("document.process_failed", document_id=document_id, error=str(e))
            await db.rollback()


@celery_app.task(name="app.tasks.resume_processing_tasks.process_resume")
def process_resume(document_id: str):
    asyncio.run(_process_resume_async(document_id))


async def _generate_job_embedding_async(job_id: str):
    async with async_session() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        if not job:
            log.error("job.embedding_not_found", job_id=job_id)
            return

        try:
            embedding = await generate_embedding(job.description)
            job.embedding = embedding
            await db.commit()
            log.info("job.embedding_generated", job_id=job_id)
        except Exception as e:
            log.error("job.embedding_failed", job_id=job_id, error=str(e))
            await db.rollback()


@celery_app.task(name="app.tasks.resume_processing_tasks.generate_job_embedding")
def generate_job_embedding(job_id: str):
    asyncio.run(_generate_job_embedding_async(job_id))
