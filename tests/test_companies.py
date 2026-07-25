import uuid
from httpx import AsyncClient


async def test_list_companies(client: AsyncClient):
    resp = await client.get("/companies/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "total_pages" in data
    assert "has_next" in data
    assert "has_previous" in data


async def test_get_my_company(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/companies/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestCorp"
    assert "open_jobs_count" in data


async def test_get_my_company_no_token(client: AsyncClient):
    resp = await client.get("/companies/me")
    assert resp.status_code == 403


async def test_get_my_company_candidate_forbidden(client: AsyncClient, candidate_token: str):
    resp = await client.get("/companies/me", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 403


async def test_update_my_company(client: AsyncClient, recruiter_token: str):
    resp = await client.patch(
        "/companies/me",
        json={"industry": "Tech", "location": "San Francisco"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["industry"] == "Tech"
    assert data["location"] == "San Francisco"


async def test_update_my_company_no_fields(client: AsyncClient, recruiter_token: str):
    resp = await client.patch(
        "/companies/me",
        json={},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resp.status_code == 422


async def test_get_company_by_id(client: AsyncClient, recruiter_token: str):
    me_resp = await client.get("/companies/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    company_id = me_resp.json()["id"]

    resp = await client.get(f"/companies/{company_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TestCorp"


async def test_get_company_not_found(client: AsyncClient):
    resp = await client.get("/companies/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_get_company_jobs(client: AsyncClient, recruiter_token: str, job_id: str):
    me_resp = await client.get("/companies/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    company_id = me_resp.json()["id"]

    resp = await client.get(f"/companies/{company_id}/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert any(j["id"] == job_id for j in data["items"])


async def test_get_company_jobs_not_found(client: AsyncClient):
    resp = await client.get("/companies/00000000-0000-0000-0000-000000000000/jobs")
    assert resp.status_code == 404
