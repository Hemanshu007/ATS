import pytest
from httpx import AsyncClient


async def test_apply(client: AsyncClient, candidate_token: str, job_id: str):
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("resume.pdf", b"content", "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["current_status"] == "applied"
    assert data["job_id"] == job_id


async def test_apply_duplicate(client: AsyncClient, candidate_token: str, job_id: str):
    # First application
    await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("r.pdf", b"x", "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    # Duplicate
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("r.pdf", b"x", "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 400
    assert "Already applied" in resp.json()["detail"]


async def test_apply_closed_job(client: AsyncClient, candidate_token: str, recruiter_token: str):
    # Create and close a job
    resp = await client.post("/jobs/", json={"title": "Closed", "description": "X"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    jid = resp.json()["id"]
    await client.patch(f"/jobs/{jid}/status", json={"status": "closed"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.post("/applications/", data={"job_id": jid},
        files={"resume": ("r.pdf", b"x", "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 400
    assert "closed" in resp.json()["detail"]


async def test_apply_recruiter_forbidden(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("r.pdf", b"x", "application/pdf")},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 403


async def test_my_applications(client: AsyncClient, candidate_token: str, application_id: str):
    resp = await client.get("/applications/me",
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_list_applications_for_job(client: AsyncClient, recruiter_token: str, job_id: str, application_id: str):
    resp = await client.get(f"/applications/job/{job_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_list_applications_not_owner(client: AsyncClient, job_id: str):
    resp = await client.post("/auth/register", json={
        "email": "other2@test.com", "password": "pass1234",
        "role": "recruiter", "name": "X", "company_name": "Y"
    })
    token = resp.json()["access_token"]
    resp = await client.get(f"/applications/job/{job_id}",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_update_status(client: AsyncClient, recruiter_token: str, application_id: str):
    resp = await client.patch(f"/applications/{application_id}/status",
        json={"status": "screening", "notes": "Good resume"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "screening"


async def test_update_status_not_found(client: AsyncClient, recruiter_token: str):
    resp = await client.patch("/applications/00000000-0000-0000-0000-000000000000/status",
        json={"status": "screening"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 404


async def test_get_history(client: AsyncClient, recruiter_token: str, application_id: str):
    # Update status to create history
    await client.patch(f"/applications/{application_id}/status",
        json={"status": "screening"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.get(f"/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2
    assert history[0]["status"] == "applied"
    assert history[1]["status"] == "screening"
