"""Full integration flow test to cover happy path code."""
from httpx import AsyncClient


async def test_full_recruiter_flow(client: AsyncClient):
    """Complete recruiter flow: register → create job → list → close."""
    # Register
    r = await client.post("/auth/register", json={
        "email": "flow_r@test.com", "password": "pass1234",
        "role": "recruiter", "name": "FlowR", "company_name": "FlowCorp"
    })
    assert r.status_code == 201
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Create job
    r = await client.post("/jobs/", json={
        "title": "Flow Job", "description": "Desc", "location": "NYC", "job_type": "remote"
    }, headers=h)
    assert r.status_code == 201
    job = r.json()
    assert job["company"]["name"] == "FlowCorp"
    job_id = job["id"]

    # List jobs
    r = await client.get("/jobs/")
    assert any(j["id"] == job_id for j in r.json()["items"])

    # Get job
    r = await client.get(f"/jobs/{job_id}")
    assert r.json()["title"] == "Flow Job"

    # Close job
    r = await client.patch(f"/jobs/{job_id}/status", json={"status": "closed"}, headers=h)
    assert r.json()["status"] == "closed"


async def test_full_candidate_flow(client: AsyncClient):
    """Complete candidate flow: register → apply → check status."""
    # Setup: recruiter + job
    r = await client.post("/auth/register", json={
        "email": "flow_r2@test.com", "password": "pass1234",
        "role": "recruiter", "name": "R2", "company_name": "C2"
    })
    rt = r.json()["access_token"]
    r = await client.post("/jobs/", json={"title": "J2", "description": "D2"},
        headers={"Authorization": f"Bearer {rt}"})
    job_id = r.json()["id"]

    # Register candidate
    r = await client.post("/auth/register", json={
        "email": "flow_c@test.com", "password": "pass1234",
        "role": "candidate", "name": "FlowC"
    })
    ct = r.json()["access_token"]
    ch = {"Authorization": f"Bearer {ct}"}

    # Apply
    r = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("cv.pdf", b"resume data", "application/pdf")},
        headers=ch)
    assert r.status_code == 201
    app_id = r.json()["id"]

    # My applications
    r = await client.get("/applications/me", headers=ch)
    assert any(a["id"] == app_id for a in r.json()["items"])


async def test_full_interview_and_notes_flow(client: AsyncClient):
    """Recruiter manages application: status update → interview → notes."""
    # Setup
    r = await client.post("/auth/register", json={
        "email": "flow_r3@test.com", "password": "pass1234",
        "role": "recruiter", "name": "R3", "company_name": "C3"
    })
    rt = r.json()["access_token"]
    rh = {"Authorization": f"Bearer {rt}"}

    r = await client.post("/jobs/", json={"title": "J3", "description": "D3"}, headers=rh)
    job_id = r.json()["id"]

    r = await client.post("/auth/register", json={
        "email": "flow_c3@test.com", "password": "pass1234",
        "role": "candidate", "name": "C3"
    })
    ct = r.json()["access_token"]
    r = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("cv.pdf", b"data", "application/pdf")},
        headers={"Authorization": f"Bearer {ct}"})
    app_id = r.json()["id"]

    # List applications for job
    r = await client.get(f"/applications/job/{job_id}", headers=rh)
    assert r.json()["total"] == 1

    # Update status
    r = await client.patch(f"/applications/{app_id}/status",
        json={"status": "screening", "notes": "Good"}, headers=rh)
    assert r.json()["current_status"] == "screening"

    # History
    r = await client.get(f"/applications/{app_id}/history", headers=rh)
    assert len(r.json()) >= 2

    # Interview
    r = await client.post("/interviews/", json={
        "application_id": app_id, "round_number": 1,
        "scheduled_at": "2027-05-01T10:00:00"
    }, headers=rh)
    assert r.status_code == 201
    iid = r.json()["id"]

    # List interviews
    r = await client.get(f"/interviews/application/{app_id}", headers=rh)
    assert len(r.json()) == 1

    # Update outcome
    r = await client.patch(f"/interviews/{iid}/outcome",
        json={"outcome": "pass", "notes": "Great"}, headers=rh)
    assert r.json()["outcome"] == "pass"

    # Notes
    r = await client.post(f"/applications/{app_id}/notes",
        json={"content": "Internal note"}, headers=rh)
    assert r.status_code == 201

    r = await client.get(f"/applications/{app_id}/notes", headers=rh)
    assert len(r.json()) == 1
