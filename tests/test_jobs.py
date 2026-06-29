import pytest
from httpx import AsyncClient


async def test_create_job(client: AsyncClient, recruiter_token: str):
    resp = await client.post("/jobs/", json={
        "title": "Engineer", "description": "Build things",
        "location": "NYC", "job_type": "onsite"
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Engineer"
    assert data["status"] == "open"
    assert data["company"]["name"] == "TestCorp"


async def test_create_job_candidate_forbidden(client: AsyncClient, candidate_token: str):
    resp = await client.post("/jobs/", json={
        "title": "X", "description": "Y"
    }, headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 403


async def test_list_jobs(client: AsyncClient, job_id: str):
    resp = await client.get("/jobs/")
    assert resp.status_code == 200
    data = resp.json()
    jobs = data["items"]
    assert len(jobs) >= 1
    assert any(j["id"] == job_id for j in jobs)


async def test_get_job(client: AsyncClient, job_id: str):
    resp = await client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


async def test_get_job_not_found(client: AsyncClient):
    resp = await client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_close_job(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.patch(f"/jobs/{job_id}/status", json={"status": "closed"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


async def test_close_job_not_owner(client: AsyncClient, job_id: str):
    # Register another recruiter
    resp = await client.post("/auth/register", json={
        "email": "other_recruiter@test.com", "password": "pass1234",
        "role": "recruiter", "name": "Other", "company_name": "OtherCorp"
    })
    other_token = resp.json()["access_token"]
    resp = await client.patch(f"/jobs/{job_id}/status", json={"status": "closed"},
        headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403


async def test_close_job_not_found(client: AsyncClient, recruiter_token: str):
    resp = await client.patch("/jobs/00000000-0000-0000-0000-000000000000/status",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 404


async def test_closed_job_not_in_list(client: AsyncClient, recruiter_token: str):
    # Create and close a job
    resp = await client.post("/jobs/", json={
        "title": "Temp", "description": "Temp"
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    jid = resp.json()["id"]
    await client.patch(f"/jobs/{jid}/status", json={"status": "closed"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.get("/jobs/")
    assert not any(j["id"] == jid for j in resp.json()["items"])
