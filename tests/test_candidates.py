import uuid
from httpx import AsyncClient


async def test_get_profile(client: AsyncClient, candidate_token: str):
    resp = await client.get("/candidates/me/profile", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestCandidate"
    assert "email" in data
    assert "id" in data


async def test_get_profile_no_token(client: AsyncClient):
    resp = await client.get("/candidates/me/profile")
    assert resp.status_code == 403


async def test_get_profile_recruiter_forbidden(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/candidates/me/profile", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 403


async def test_update_profile(client: AsyncClient, candidate_token: str):
    resp = await client.patch(
        "/candidates/me/profile",
        json={"name": "UpdatedName", "phone": "1234567890", "location": "NYC"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "UpdatedName"
    assert data["phone"] == "1234567890"
    assert data["location"] == "NYC"


async def test_update_profile_no_fields(client: AsyncClient, candidate_token: str):
    resp = await client.patch(
        "/candidates/me/profile",
        json={},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert resp.status_code == 422


async def test_candidate_dashboard(client: AsyncClient, candidate_token: str):
    resp = await client.get("/candidates/me/dashboard", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_applications" in data
    assert "status_breakdown" in data
    assert "recent_applications" in data
    assert data["total_applications"] == 0
    assert isinstance(data["status_breakdown"], dict)
    assert isinstance(data["recent_applications"], list)


async def test_candidate_dashboard_no_token(client: AsyncClient):
    resp = await client.get("/candidates/me/dashboard")
    assert resp.status_code == 403
