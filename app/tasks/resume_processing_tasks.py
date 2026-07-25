import asyncio
import logging
import os
import uuid
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.config import settings
from app.database import async_session
from app.models.document import Document
from app.models.job import Job
from app.services.llm_extraction import extract_text_from_pdf, extract_resume_data
from app.services.embeddings import generate_embedding

logger = logging.getLogger("ats.tasks")


async def _process_resume_async(document_id: str):
    async with async_session() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if not document:
            logger.error(f"Document {document_id} not found for processing")
            return

        try:
            full_path = os.path.join(settings.UPLOAD_DIR, document.file_path)
            with open(full_path, "rb") as f:
                file_bytes = f.read()

            text = extract_text_from_pdf(file_bytes)
            if not text.strip():
                logger.warning(f"No text extracted from document {document_id}")
                return

            extraction = await extract_resume_data(text)

            embedding_text = " ".join(extraction.skills) + " " + " ".join(
                wh.role + " " + wh.company for wh in extraction.work_history
            )
            embedding = await generate_embedding(embedding_text)

            document.parsed_data = extraction.model_dump()
            document.embedding = embedding
            document.parsed_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Document {document_id} processed successfully")

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            await db.rollback()


@celery_app.task(name="app.tasks.resume_processing_tasks.process_resume")
def process_resume(document_id: str):
    asyncio.run(_process_resume_async(document_id))


async def _generate_job_embedding_async(job_id: str):
    async with async_session() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        if not job:
            logger.error(f"Job {job_id} not found for embedding")
            return

        try:
            embedding = await generate_embedding(job.description)
            job.embedding = embedding
            await db.commit()
            logger.info(f"Job {job_id} embedding generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate embedding for job {job_id}: {e}")
            await db.rollback()


@celery_app.task(name="app.tasks.resume_processing_tasks.generate_job_embedding")
def generate_job_embedding(job_id: str):
    asyncio.run(_generate_job_embedding_async(job_id))
