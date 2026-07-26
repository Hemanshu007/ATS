"""Tests for POST /jobs/{job_id}/search — conversational RAG search endpoint."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from tests.conftest import TestSession, override_get_db
from app.main import app
from app.models.document import Document
from app.models.candidate import Candidate
from app.models.user import User
from app.models.job import Job
from app.core.security import hash_password
from app.database import get_db
from app.services.llm_search import SearchResult, CandidateMatchExplanation


MOCK_SEARCH_RESULT = SearchResult(
    query="find candidates with Python experience",
    matches=[
        CandidateMatchExplanation(
            document_id=str(uuid.uuid4()),
            candidate_id=str(uuid.uuid4()),
            relevance_summary="Strong Python background with FastAPI experience.",
            supporting_evidence=["Skills: Python, FastAPI, PostgreSQL"],
        )
    ],
)


async def test_search_requires_recruiter_auth(client: AsyncClient, candidate_token: str, job_id: str):
    resp = await client.post(
        f"/jobs/{job_id}/search",
        json={"query": "find python developers"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 403


async def test_search_no_token(client: AsyncClient, job_id: str):
    resp = await client.post(f"/jobs/{job_id}/search", json={"query": "test"})
    assert resp.status_code in (401, 403)


async def test_search_job_not_found(client: AsyncClient, recruiter_token: str):
    resp = await client.post(
        "/jobs/00000000-0000-0000-0000-000000000000/search",
        json={"query": "test"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_search_not_your_job(client: AsyncClient, job_id: str):
    resp = await client.post("/auth/register", json={
        "email": f"search_other_{uuid.uuid4().hex[:6]}@test.com",
        "password": "pass1234",
        "role": "recruiter",
        "name": "Other",
        "company_name": "OtherCorp",
    })
    other_token = resp.json()["access_token"]
    resp = await client.post(
        f"/jobs/{job_id}/search",
        json={"query": "test"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


async def test_search_empty_results(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 10):
        with patch("app.routers.matching._retrieve_candidates", new_callable=AsyncMock, return_value=[]):
            with patch("app.routers.matching.generate_search_explanation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = SearchResult(query="test", matches=[])
                resp = await client.post(
                    f"/jobs/{job_id}/search",
                    json={"query": "find someone with obscure skill XYZ"},
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["query"] == "test"
                assert data["matches"] == []
                mock_gen.assert_called_once()


async def test_search_returns_grounded_results(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_doc.candidate_id = uuid.uuid4()
    mock_doc.parsed_data = {"name": "TestCandidate", "skills": ["Python"]}

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 10):
        with patch("app.routers.matching._retrieve_candidates", new_callable=AsyncMock, return_value=[(mock_doc, 0.3)]):
            with patch("app.routers.matching.generate_search_explanation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = MOCK_SEARCH_RESULT
                resp = await client.post(
                    f"/jobs/{job_id}/search",
                    json={"query": "find candidates with Python experience"},
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["query"] == "find candidates with Python experience"
                assert len(data["matches"]) == 1
                match = data["matches"][0]
                assert "relevance_summary" in match
                assert "supporting_evidence" in match
                assert "document_id" in match
                assert "candidate_id" in match
                assert isinstance(match["supporting_evidence"], list)


async def test_search_embedding_failure_returns_503(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, side_effect=Exception("API down")):
        resp = await client.post(
            f"/jobs/{job_id}/search",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert resp.status_code == 503
        assert "retry" in resp.json()["detail"].lower()


async def test_search_llm_failure_returns_503(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 10):
        with patch("app.routers.matching._retrieve_candidates", new_callable=AsyncMock, return_value=[]):
            with patch("app.routers.matching.generate_search_explanation", new_callable=AsyncMock, side_effect=Exception("LLM timeout")):
                resp = await client.post(
                    f"/jobs/{job_id}/search",
                    json={"query": "test"},
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 503
                assert "retry" in resp.json()["detail"].lower()


async def test_search_respects_limit(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 10):
        with patch("app.routers.matching._retrieve_candidates", new_callable=AsyncMock, return_value=[]) as mock_retrieve:
            with patch("app.routers.matching.generate_search_explanation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = SearchResult(query="test", matches=[])
                resp = await client.post(
                    f"/jobs/{job_id}/search?limit=3",
                    json={"query": "test"},
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 200
                mock_retrieve.assert_called_once()
                call_args = mock_retrieve.call_args
                assert call_args[0][1] == 3


async def test_search_limit_rejects_invalid_values(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    resp = await client.post(
        f"/jobs/{job_id}/search?limit=0",
        json={"query": "test"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 422

    resp = await client.post(
        f"/jobs/{job_id}/search?limit=20",
        json={"query": "test"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 422


async def test_search_missing_query(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.post(
        f"/jobs/{job_id}/search",
        json={},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 422


async def test_search_does_not_affect_application_status(client: AsyncClient, recruiter_token: str, job_id: str, application_id: str):
    async with TestSession() as db:
        from app.models.application import Application
        app_record = await db.get(Application, uuid.UUID(application_id))
        original_status = app_record.current_status

        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

    with patch("app.routers.matching.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 10):
        with patch("app.routers.matching._retrieve_candidates", new_callable=AsyncMock, return_value=[]):
            with patch("app.routers.matching.generate_search_explanation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = SearchResult(query="test", matches=[])
                await client.post(
                    f"/jobs/{job_id}/search",
                    json={"query": "test"},
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )

    async with TestSession() as verify_db:
        app_after = await verify_db.get(Application, uuid.UUID(application_id))
        assert app_after.current_status == original_status
