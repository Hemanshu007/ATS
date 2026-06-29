import pytest
from httpx import AsyncClient


async def test_create_note(client: AsyncClient, recruiter_token: str, application_id: str):
    resp = await client.post(f"/applications/{application_id}/notes",
        json={"content": "Strong candidate"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 201
    assert resp.json()["content"] == "Strong candidate"


async def test_list_notes(client: AsyncClient, recruiter_token: str, application_id: str):
    await client.post(f"/applications/{application_id}/notes",
        json={"content": "Note 1"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    await client.post(f"/applications/{application_id}/notes",
        json={"content": "Note 2"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.get(f"/applications/{application_id}/notes",
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_create_note_candidate_forbidden(client: AsyncClient, candidate_token: str, application_id: str):
    resp = await client.post(f"/applications/{application_id}/notes",
        json={"content": "Hack"},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 403
