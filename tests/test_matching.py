"""Tests for the GET /jobs/{job_id}/matches endpoint."""
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


async def test_matching_requires_recruiter_auth(client: AsyncClient, candidate_token: str, job_id: str):
    resp = await client.get(
        f"/jobs/{job_id}/matches",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 403


async def test_matching_no_token(client: AsyncClient, job_id: str):
    resp = await client.get(f"/jobs/{job_id}/matches")
    assert resp.status_code in (401, 403)


async def test_matching_job_not_found(client: AsyncClient, recruiter_token: str):
    resp = await client.get(
        "/jobs/00000000-0000-0000-0000-000000000000/matches",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_matching_not_your_job(client: AsyncClient, job_id: str):
    resp = await client.post("/auth/register", json={
        "email": f"match_other_{uuid.uuid4().hex[:6]}@test.com",
        "password": "pass1234",
        "role": "recruiter",
        "name": "Other",
        "company_name": "OtherCorp",
    })
    other_token = resp.json()["access_token"]
    resp = await client.get(
        f"/jobs/{job_id}/matches",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


async def test_matching_job_not_processed(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        assert job.embedding is None

    resp = await client.get(
        f"/jobs/{job_id}/matches",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 404
    assert "not yet processed" in resp.json()["detail"].lower()


async def test_matching_returns_ranked_results(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

        user = User(email=f"match_{uuid.uuid4().hex[:6]}@test.com", role="candidate", hashed_password=hash_password("pass1234"))
        db.add(user)
        await db.flush()

        candidate = Candidate(user_id=user.id, name="MatchCandidate")
        db.add(candidate)
        await db.flush()

        doc = Document(
            candidate_id=candidate.id,
            file_path="resumes/test/resume.pdf",
            original_filename="resume.pdf",
            parsed_data={"name": "MatchCandidate", "skills": ["Python", "FastAPI"]},
            embedding=[0.2] * 10,
        )
        db.add(doc)
        await db.commit()

    mock_doc = MagicMock()
    mock_doc.id = doc.id
    mock_doc.candidate_id = candidate.id
    mock_doc.parsed_data = {"name": "MatchCandidate", "skills": ["Python", "FastAPI"]}

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_doc, 0.15)]

    mock_distance_expr = MagicMock()
    mock_distance_expr.label.return_value = MagicMock(name="distance_col")

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_embedding_col = MagicMock()
    mock_embedding_col.cosine_distance.return_value = mock_distance_expr
    mock_embedding_col.isnot.return_value = MagicMock(name="isnot_expr")

    async def override_db_for_matching():
        async with TestSession() as session:
            session.execute = AsyncMock(return_value=mock_result)
            yield session

    app.dependency_overrides[get_db] = override_db_for_matching
    try:
        with patch("app.routers.matching.select", return_value=mock_query):
            with patch.object(Document, "embedding", mock_embedding_col):
                resp = await client.get(
                    f"/jobs/{job_id}/matches",
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["job_id"] == job_id
                assert len(data["matches"]) == 1
                match = data["matches"][0]
                assert match["similarity_score"] == 0.85
                assert match["parsed_data"]["name"] == "MatchCandidate"
                assert "document_id" in match
                assert "candidate_id" in match
    finally:
        app.dependency_overrides[get_db] = override_get_db


async def test_matching_respects_limit(client: AsyncClient, recruiter_token: str, job_id: str):
    async with TestSession() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.embedding = [0.1] * 10
        await db.commit()

        for i in range(3):
            user = User(email=f"limit_{uuid.uuid4().hex[:6]}@test.com", role="candidate", hashed_password=hash_password("pass1234"))
            db.add(user)
            await db.flush()
            candidate = Candidate(user_id=user.id, name=f"Candidate{i}")
            db.add(candidate)
            await db.flush()
            doc = Document(
                candidate_id=candidate.id,
                file_path=f"resumes/test/resume_{i}.pdf",
                original_filename=f"resume_{i}.pdf",
                embedding=[0.2] * 10,
            )
            db.add(doc)
        await db.commit()

    mock_result = MagicMock()
    mock_result.all.return_value = [
        (MagicMock(parsed_data={"name": f"C{i}"}), 0.15) for i in range(2)
    ]

    mock_distance_expr = MagicMock()
    mock_distance_expr.label.return_value = MagicMock(name="distance_col")

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_embedding_col = MagicMock()
    mock_embedding_col.cosine_distance.return_value = mock_distance_expr
    mock_embedding_col.isnot.return_value = MagicMock(name="isnot_expr")

    async def override_db_for_matching():
        async with TestSession() as session:
            session.execute = AsyncMock(return_value=mock_result)
            yield session

    app.dependency_overrides[get_db] = override_db_for_matching
    try:
        with patch("app.routers.matching.select", return_value=mock_query):
            with patch.object(Document, "embedding", mock_embedding_col):
                resp = await client.get(
                    f"/jobs/{job_id}/matches?limit=2",
                    headers={"Authorization": f"Bearer {recruiter_token}"},
                )
                assert resp.status_code == 200
                assert len(resp.json()["matches"]) <= 2
    finally:
        app.dependency_overrides[get_db] = override_get_db
