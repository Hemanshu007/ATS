"""Unit tests for RAG services: PDF extraction, LLM parsing, embeddings."""
import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_extraction import (
    extract_text_from_pdf,
    extract_resume_data,
    ResumeExtraction,
)
from app.services.embeddings import generate_embedding


# --- Helper: create a minimal valid PDF with text ---

def _make_test_pdf(text: str = "Hello World") -> bytes:
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


def _ensure_openai_mock():
    """Inject a fake openai module if not installed."""
    if "openai" not in sys.modules:
        fake_openai = ModuleType("openai")
        fake_openai.AsyncOpenAI = MagicMock
        sys.modules["openai"] = fake_openai
    return sys.modules["openai"]


# --- extract_text_from_pdf ---

def test_extract_text_from_pdf():
    pdf_bytes = _make_test_pdf("John Smith Python Developer")
    text = extract_text_from_pdf(pdf_bytes)
    assert "John Smith" in text
    assert "Python Developer" in text


def test_extract_text_from_multiline_pdf():
    pdf_bytes = _make_test_pdf("Line1 Line2 Line3")
    text = extract_text_from_pdf(pdf_bytes)
    assert "Line1" in text
    assert "Line2" in text
    assert "Line3" in text


# --- extract_resume_data ---

async def test_extract_resume_data_success():
    _ensure_openai_mock()

    fake_response = {
        "name": "John Doe",
        "email": "john@test.com",
        "phone": "1234567890",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "years_of_experience": 5.0,
        "education": [{"degree": "BS Computer Science", "institution": "MIT"}],
        "work_history": [{"role": "Backend Dev", "company": "Acme", "duration": "2 years"}],
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(fake_response)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch("app.services.llm_extraction.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await extract_resume_data("John Doe\nPython Developer\njohn@test.com")

    assert isinstance(result, ResumeExtraction)
    assert result.name == "John Doe"
    assert result.email == "john@test.com"
    assert result.skills == ["Python", "FastAPI", "PostgreSQL"]
    assert result.years_of_experience == 5.0
    assert len(result.education) == 1
    assert result.education[0].degree == "BS Computer Science"
    assert len(result.work_history) == 1
    assert result.work_history[0].company == "Acme"

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs.kwargs["temperature"] == 0
    assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}


async def test_extract_resume_data_missing_api_key():
    with patch("app.services.llm_extraction.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await extract_resume_data("Some resume text")


# --- generate_embedding ---

async def test_generate_embedding_success():
    _ensure_openai_mock()

    fake_embedding = [0.1] * 1536
    mock_resp = MagicMock()
    mock_resp.data = [MagicMock(embedding=fake_embedding)]

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_resp)

    with patch("app.services.embeddings.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await generate_embedding("Python developer with 5 years experience")

    assert isinstance(result, list)
    assert len(result) == 1536
    assert result == fake_embedding

    mock_client.embeddings.create.assert_called_once()
    call_kwargs = mock_client.embeddings.create.call_args
    assert call_kwargs.kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs.kwargs["input"] == "Python developer with 5 years experience"


async def test_generate_embedding_missing_api_key():
    with patch("app.services.embeddings.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await generate_embedding("Some text")
