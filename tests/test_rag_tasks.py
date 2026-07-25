"""Unit tests for RAG Celery tasks: process_resume and generate_job_embedding."""
import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import TestSession
from app.models.document import Document
from app.models.candidate import Candidate
from app.models.user import User
from app.models.job import Job
from app.core.config import settings
from app.core.security import hash_password

import app.tasks.resume_processing_tasks as tasks_module
from app.services.llm_extraction import ResumeExtraction, Education, WorkHistory
from app.tasks.resume_processing_tasks import (
    _process_resume_async,
    _generate_job_embedding_async,
)


FAKE_EMBEDDING = [0.1] * 10
FAKE_EXTRACTION = ResumeExtraction(
    name="John Smith",
    email="john@test.com",
    phone="123",
    skills=["Python", "FastAPI"],
    years_of_experience=3.0,
    education=[],
    work_history=[WorkHistory(role="Dev", company="Acme", duration="2 years")],
)


def _make_test_pdf(text: str = "John Smith Python Developer") -> bytes:
    stream_data = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 4 0 R >> >>"
        b" /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    objects.append(
        f"5 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1")
        + stream_data
        + b"\nendstream\nendobj\n"
    )
    body = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref_start = len(body)
    num = len(objects) + 1
    body += f"xref\n0 {num}\n".encode("latin-1")
    body += b"0000000000 65535 f \n"
    for off in offsets:
        body += f"{off:010d} 00000 n \n".encode("latin-1")
    body += f"trailer\n<< /Size {num} /Root 1 0 R >>\n".encode("latin-1")
    body += f"startxref\n{xref_start}\n%%EOF\n".encode("latin-1")
    return body


async def _setup_document():
    """Create a candidate, user, and document in the test DB. Returns (document_id, file_path)."""
    async with TestSession() as db:
        user = User(email=f"task_test_{uuid.uuid4().hex[:6]}@test.com", role="candidate", hashed_password=hash_password("pass1234"))
        db.add(user)
        await db.flush()

        candidate = Candidate(user_id=user.id, name="TaskTester")
        db.add(candidate)
        await db.flush()

        file_name = f"resume_{uuid.uuid4().hex[:6]}.pdf"
        file_path = f"resumes/{uuid.uuid4()}/{file_name}"
        doc = Document(
            candidate_id=candidate.id,
            file_path=file_path,
            original_filename=file_name,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc, file_path


async def _setup_job():
    """Create a job in the test DB. Returns job."""
    async with TestSession() as db:
        from app.models.recruiter import Recruiter
        from app.models.company import Company

        user = User(email=f"job_task_{uuid.uuid4().hex[:6]}@test.com", role="recruiter", hashed_password=hash_password("pass1234"))
        db.add(user)
        await db.flush()

        company = Company(name="TaskCorp", industry="Tech", location="Remote")
        db.add(company)
        await db.flush()

        recruiter = Recruiter(user_id=user.id, company_id=company.id, name="TaskRecruiter")
        db.add(recruiter)
        await db.flush()

        job = Job(
            title="Python Developer",
            description="Python developer with FastAPI experience",
            location="Remote",
            job_type="remote",
            company_id=company.id,
            created_by=recruiter.id,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job


# --- process_resume ---

async def test_process_resume_full_flow():
    doc, file_path = await _setup_document()

    # Write a real PDF to disk
    full_path = os.path.join(settings.UPLOAD_DIR, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(_make_test_pdf("John Smith Python Developer"))

    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        with patch.object(tasks_module, "extract_resume_data", new_callable=AsyncMock, return_value=FAKE_EXTRACTION) as mock_extract:
            with patch.object(tasks_module, "generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING) as mock_embed:
                await _process_resume_async(str(doc.id))

        mock_extract.assert_called_once()
        called_text = mock_extract.call_args[0][0]
        assert "John Smith" in called_text

        mock_embed.assert_called_once()
        embed_text = mock_embed.call_args[0][0]
        assert "Python" in embed_text
        assert "Acme" in embed_text

        # Verify document was updated in DB
        async with TestSession() as db:
            updated_doc = await db.get(Document, doc.id)
            assert updated_doc.parsed_data is not None
            assert updated_doc.parsed_data["name"] == "John Smith"
            assert updated_doc.embedding == FAKE_EMBEDDING
            assert updated_doc.parsed_at is not None
    finally:
        tasks_module.async_session = original_session


async def test_process_resume_document_not_found():
    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        fake_id = str(uuid.uuid4())
        # Should not raise — just logs and returns
        await _process_resume_async(fake_id)
    finally:
        tasks_module.async_session = original_session


async def test_process_resume_empty_text():
    doc, file_path = await _setup_document()

    # Write an empty (but valid) PDF
    full_path = os.path.join(settings.UPLOAD_DIR, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(_make_test_pdf(""))

    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        with patch.object(tasks_module, "extract_resume_data", new_callable=AsyncMock) as mock_extract:
            await _process_resume_async(str(doc.id))
            mock_extract.assert_not_called()
    finally:
        tasks_module.async_session = original_session


async def test_process_resume_service_error():
    doc, file_path = await _setup_document()

    full_path = os.path.join(settings.UPLOAD_DIR, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(_make_test_pdf("Some text"))

    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        with patch.object(tasks_module, "extract_resume_data", new_callable=AsyncMock, side_effect=ValueError("API error")):
            # Should not raise — catches exception and rolls back
            await _process_resume_async(str(doc.id))

        # Verify document was NOT updated
        async with TestSession() as db:
            doc_ref = await db.get(Document, doc.id)
            assert doc_ref.parsed_data is None
            assert doc_ref.embedding is None
    finally:
        tasks_module.async_session = original_session


# --- generate_job_embedding ---

async def test_generate_job_embedding_full_flow():
    job = await _setup_job()

    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        with patch.object(tasks_module, "generate_embedding", new_callable=AsyncMock, return_value=FAKE_EMBEDDING) as mock_embed:
            await _generate_job_embedding_async(str(job.id))

        mock_embed.assert_called_once()
        assert mock_embed.call_args[0][0] == "Python developer with FastAPI experience"

        async with TestSession() as db:
            updated_job = await db.get(Job, job.id)
            assert updated_job.embedding == FAKE_EMBEDDING
    finally:
        tasks_module.async_session = original_session


async def test_generate_job_embedding_not_found():
    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        fake_id = str(uuid.uuid4())
        # Should not raise — just logs and returns
        await _generate_job_embedding_async(fake_id)
    finally:
        tasks_module.async_session = original_session


async def test_generate_job_embedding_service_error():
    job = await _setup_job()

    original_session = tasks_module.async_session
    tasks_module.async_session = TestSession
    try:
        with patch.object(tasks_module, "generate_embedding", new_callable=AsyncMock, side_effect=ValueError("API error")):
            await _generate_job_embedding_async(str(job.id))

        async with TestSession() as db:
            updated_job = await db.get(Job, job.id)
            assert updated_job.embedding is None
    finally:
        tasks_module.async_session = original_session
