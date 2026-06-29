import pytest
from httpx import AsyncClient


async def test_register_recruiter(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "newrecruiter@test.com", "password": "pass1234",
        "role": "recruiter", "name": "Alice", "company_name": "Corp"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "recruiter"
    assert "access_token" in data


async def test_register_candidate(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "newcandidate@test.com", "password": "pass1234",
        "role": "candidate", "name": "Bob"
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "candidate"


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "pass1234", "role": "candidate", "name": "X"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


async def test_register_recruiter_missing_company(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "nocompany@test.com", "password": "pass1234",
        "role": "recruiter", "name": "X"
    })
    assert resp.status_code == 400
    assert "company_name" in resp.json()["detail"]


async def test_register_invalid_role(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "badrole@test.com", "password": "pass1234",
        "role": "admin", "name": "X"
    })
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "login@test.com", "password": "pass1234",
        "role": "candidate", "name": "X"
    })
    resp = await client.post("/auth/login", json={
        "email": "login@test.com", "password": "pass1234"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrongpw@test.com", "password": "pass1234",
        "role": "candidate", "name": "X"
    })
    resp = await client.post("/auth/login", json={
        "email": "wrongpw@test.com", "password": "wrong"
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@test.com", "password": "pass1234"
    })
    assert resp.status_code == 401


async def test_me_recruiter(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "recruiter"
    assert "company_id" in data["profile"]


async def test_me_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "candidate"
    assert "location" in data["profile"]


async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


async def test_me_no_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403
