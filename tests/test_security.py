"""Tests for new security features: file validation, ownership, password rules."""
import uuid

import pytest
from httpx import AsyncClient


async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "short@test.com", "password": "short",
        "role": "candidate", "name": "X"
    })
    assert resp.status_code == 422


async def test_upload_invalid_file_type(client: AsyncClient, candidate_token: str, job_id: str):
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("hack.exe", b"malware", "application/octet-stream")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


async def test_upload_oversized_file(client: AsyncClient, candidate_token: str, job_id: str):
    big_content = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("big.pdf", big_content, "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    assert resp.status_code == 400
    assert "5MB" in resp.json()["detail"]


async def test_invalid_job_status_value(client: AsyncClient, recruiter_token: str, job_id: str):
    resp = await client.patch(f"/jobs/{job_id}/status", json={"status": "banana"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 422


async def test_invalid_application_status_value(client: AsyncClient, recruiter_token: str, application_id: str):
    resp = await client.patch(f"/applications/{application_id}/status",
        json={"status": "banana"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 422


async def test_invalid_interview_outcome(client: AsyncClient, recruiter_token: str, application_id: str):
    # Create interview first
    resp = await client.post("/interviews/", json={
        "application_id": application_id, "round_number": 99,
        "scheduled_at": "2027-01-01T10:00:00"
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    iid = resp.json()["id"]
    resp = await client.patch(f"/interviews/{iid}/outcome",
        json={"outcome": "maybe"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 422


async def test_notes_other_recruiter_forbidden(client: AsyncClient, application_id: str):
    # Register another recruiter
    resp = await client.post("/auth/register", json={
        "email": "other_notes@test.com", "password": "pass1234",
        "role": "recruiter", "name": "Other", "company_name": "OtherCorp"
    })
    other_token = resp.json()["access_token"]
    resp = await client.post(f"/applications/{application_id}/notes",
        json={"content": "sneaky"},
        headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403


async def test_history_other_recruiter_forbidden(client: AsyncClient, application_id: str):
    resp = await client.post("/auth/register", json={
        "email": "other_hist@test.com", "password": "pass1234",
        "role": "recruiter", "name": "Other", "company_name": "OtherCorp"
    })
    other_token = resp.json()["access_token"]
    resp = await client.get(f"/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403


async def test_interview_other_recruiter_forbidden(client: AsyncClient, application_id: str):
    resp = await client.post("/auth/register", json={
        "email": "other_int@test.com", "password": "pass1234",
        "role": "recruiter", "name": "Other", "company_name": "OtherCorp"
    })
    other_token = resp.json()["access_token"]
    resp = await client.post("/interviews/", json={
        "application_id": application_id, "round_number": 1,
    }, headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403


async def test_interview_duplicate_round_number(client: AsyncClient, recruiter_token: str, application_id: str):
    await client.post("/interviews/", json={
        "application_id": application_id, "round_number": 50,
        "scheduled_at": "2027-03-01T10:00:00"
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    resp = await client.post("/interviews/", json={
        "application_id": application_id, "round_number": 50,
        "scheduled_at": "2027-03-02T10:00:00"
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert resp.status_code == 409
    assert "Round 50" in resp.json()["detail"]
