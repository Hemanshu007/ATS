import uuid
from httpx import AsyncClient


async def test_recruiter_dashboard(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/recruiters/me/dashboard", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "open_jobs" in data
    assert "closed_jobs" in data
    assert "total_applications" in data
    assert "pipeline_summary" in data
    assert data["total_jobs"] == 0
    assert data["open_jobs"] == 0
    assert data["closed_jobs"] == 0
    assert data["total_applications"] == 0


async def test_recruiter_dashboard_with_jobs(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.get("/recruiters/me/dashboard", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_jobs"] == 1
    assert data["open_jobs"] == 1
    assert data["closed_jobs"] == 0


async def test_recruiter_dashboard_no_token(client: AsyncClient):
    resp = await client.get("/recruiters/me/dashboard")
    assert resp.status_code == 403


async def test_recruiter_dashboard_candidate_forbidden(client: AsyncClient, candidate_token: str):
    resp = await client.get("/recruiters/me/dashboard", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 403


async def test_recruiter_jobs(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.get("/recruiters/me/jobs", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["title"] == "Test Job"
    assert data["items"][0]["application_count"] == 0


async def test_recruiter_jobs_empty(client: AsyncClient):
    # Register a new recruiter with no jobs
    reg = await client.post("/auth/register", json={
        "email": f"empty_{uuid.uuid4().hex[:6]}@test.com",
        "password": "pass1234",
        "role": "recruiter",
        "name": "Empty",
        "company_name": "EmptyCorp",
    })
    token = reg.json()["access_token"]
    resp = await client.get("/recruiters/me/jobs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_recruiter_jobs_no_token(client: AsyncClient):
    resp = await client.get("/recruiters/me/jobs")
    assert resp.status_code == 403
