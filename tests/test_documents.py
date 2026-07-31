import uuid
from httpx import AsyncClient
from tests.conftest import TestSession
from app.models.document import Document
from app.models.candidate import Candidate
from app.core.security import hash_password


async def test_list_my_documents_empty(client: AsyncClient, candidate_token: str):
    resp = await client.get("/documents/me", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_my_documents(client: AsyncClient, candidate_token: str, application_id: str):
    resp = await client.get("/documents/me", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert "id" in data["items"][0]
    assert "original_filename" in data["items"][0]


async def test_list_my_documents_no_token(client: AsyncClient):
    resp = await client.get("/documents/me")
    assert resp.status_code == 403


async def test_list_my_documents_recruiter_forbidden(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/documents/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 403


async def test_delete_document_success(client: AsyncClient, candidate_token: str):
    async with TestSession() as db:
        from sqlalchemy import select
        user_result = await db.execute(
            select(Candidate).where(Candidate.name == "TestCandidate")
        )
        candidate = user_result.scalar_one_or_none()
        candidate_id = candidate.id

        doc = Document(
            candidate_id=candidate_id,
            file_path="resumes/standalone.pdf",
            original_filename="standalone.pdf",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id = str(doc.id)

    resp = await client.delete(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


async def test_delete_document_active_application_blocks(client: AsyncClient, candidate_token: str, application_id: str):
    list_resp = await client.get("/documents/me", headers={"Authorization": f"Bearer {candidate_token}"})
    doc_id = list_resp.json()["items"][0]["id"]

    resp = await client.delete(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 409
    assert "application" in resp.json()["detail"].lower()


async def test_delete_document_terminal_application_still_blocks(client: AsyncClient, candidate_token: str, recruiter_token: str, application_id: str):
    """Application.document_id is a required FK with no cascade, so even a document
    linked to a terminal-status (rejected/hired) application must stay blocked from
    hard deletion — deleting it would violate referential integrity."""
    await client.patch(
        f"/applications/{application_id}/status",
        json={"status": "rejected"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    list_resp = await client.get("/documents/me", headers={"Authorization": f"Bearer {candidate_token}"})
    doc_id = list_resp.json()["items"][0]["id"]

    resp = await client.delete(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 409
    assert "application" in resp.json()["detail"].lower()


async def test_delete_document_not_found(client: AsyncClient, candidate_token: str):
    resp = await client.delete(
        "/documents/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 404


async def test_delete_document_wrong_owner(client: AsyncClient, recruiter_token: str, application_id: str):
    async with TestSession() as db:
        from sqlalchemy import select
        result = await db.execute(select(Document).limit(1))
        doc = result.scalar_one_or_none()
        if not doc:
            return
        doc_id = str(doc.id)

    resp = await client.delete(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 403
