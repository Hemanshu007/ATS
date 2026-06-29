import pytest
from httpx import AsyncClient


async def test_create_interview(client: AsyncClient, recruiter_token: str, application_id: str):
    resp = await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-07-01T10:00:00",
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["round_number"] == 1
    assert data["outcome"] == "pending"


async def test_create_interview_with_conductor(client: AsyncClient, recruiter_token: str, application_id: str):
    # Get recruiter id
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    recruiter_id = me.json()["profile"]["id"]
    resp = await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-07-02T10:00:00",
        "conducted_by": recruiter_id,
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 201


async def test_interview_overlap(client: AsyncClient, recruiter_token: str, application_id: str):
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    recruiter_id = me.json()["profile"]["id"]
    # First interview
    await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-08-01T10:00:00",
        "conducted_by": recruiter_id,
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    # Overlapping interview (within 1 hour)
    resp = await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 2,
        "scheduled_at": "2026-08-01T10:30:00",
        "conducted_by": recruiter_id,
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 409
    assert "conflicting" in resp.json()["detail"]


async def test_interview_no_overlap_different_time(client: AsyncClient, recruiter_token: str, application_id: str):
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    recruiter_id = me.json()["profile"]["id"]
    await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-09-01T10:00:00",
        "conducted_by": recruiter_id,
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    # 2 hours later — no overlap
    resp = await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 2,
        "scheduled_at": "2026-09-01T12:00:00",
        "conducted_by": recruiter_id,
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 201


async def test_list_interviews(client: AsyncClient, recruiter_token: str, application_id: str):
    await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-10-01T10:00:00",
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.get(f"/interviews/application/{application_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_update_outcome(client: AsyncClient, recruiter_token: str, application_id: str):
    resp = await client.post("/interviews/", json={
        "application_id": application_id,
        "round_number": 1,
        "scheduled_at": "2026-11-01T10:00:00",
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    interview_id = resp.json()["id"]
    resp = await client.patch(f"/interviews/{interview_id}/outcome",
        json={"outcome": "pass", "notes": "Great"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "pass"
    assert resp.json()["notes"] == "Great"


async def test_update_outcome_not_found(client: AsyncClient, recruiter_token: str):
    resp = await client.patch("/interviews/00000000-0000-0000-0000-000000000000/outcome",
        json={"outcome": "fail"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 404
