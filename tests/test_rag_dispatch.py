"""Tests that apply and create_job dispatch Celery tasks correctly."""
from unittest.mock import patch, MagicMock

from httpx import AsyncClient


async def test_apply_dispatches_process_resume(client: AsyncClient, candidate_token: str, job_id: str):
    with patch("app.tasks.resume_processing_tasks.process_resume") as mock_task:
        resp = await client.post(
            "/applications/",
            data={"job_id": job_id},
            files={"resume": ("resume.pdf", b"some resume content", "application/pdf")},
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert resp.status_code == 201
        mock_task.delay.assert_called_once()
        dispatched_id = mock_task.delay.call_args[0][0]
        assert isinstance(dispatched_id, str)
        assert len(dispatched_id) == 36  # UUID format


async def test_apply_no_dispatch_on_failure(client: AsyncClient, candidate_token: str, recruiter_token: str):
    resp = await client.post("/jobs/", json={"title": "Closed", "description": "X"},
        headers={"Authorization": f"Bearer {recruiter_token}"})
    jid = resp.json()["id"]
    await client.patch(f"/jobs/{jid}/status", json={"status": "closed"},
        headers={"Authorization": f"Bearer {recruiter_token}"})

    with patch("app.tasks.resume_processing_tasks.process_resume") as mock_task:
        resp = await client.post(
            "/applications/",
            data={"job_id": jid},
            files={"resume": ("resume.pdf", b"content", "application/pdf")},
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert resp.status_code == 400
        mock_task.delay.assert_not_called()


async def test_create_job_dispatches_generate_job_embedding(client: AsyncClient, recruiter_token: str):
    with patch("app.tasks.resume_processing_tasks.generate_job_embedding") as mock_task:
        resp = await client.post(
            "/jobs/",
            json={"title": "New Job", "description": "Build stuff", "location": "NYC", "job_type": "onsite"},
            headers={"Authorization": f"Bearer {recruiter_token}"},
        )
        assert resp.status_code == 201
        mock_task.delay.assert_called_once()
        dispatched_id = mock_task.delay.call_args[0][0]
        assert isinstance(dispatched_id, str)
        assert len(dispatched_id) == 36
