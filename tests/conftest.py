import asyncio
import os
import sys
import uuid
from typing import AsyncGenerator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["UPLOAD_DIR"] = "/tmp/ats_test_uploads"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.routers.auth import limiter

# Disable rate limiting in tests
limiter.enabled = False

engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    os.makedirs("/tmp/ats_test_uploads/resumes", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def recruiter_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/register", json={
        "email": f"recruiter_{uuid.uuid4().hex[:6]}@test.com",
        "password": "pass1234",
        "role": "recruiter",
        "name": "TestRecruiter",
        "company_name": "TestCorp",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def candidate_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/register", json={
        "email": f"candidate_{uuid.uuid4().hex[:6]}@test.com",
        "password": "pass1234",
        "role": "candidate",
        "name": "TestCandidate",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def job_id(client: AsyncClient, recruiter_token: str) -> str:
    resp = await client.post("/jobs/", json={
        "title": "Test Job",
        "description": "A test job",
        "location": "Remote",
        "job_type": "remote",
    }, headers={"Authorization": f"Bearer {recruiter_token}"})
    return resp.json()["id"]


@pytest_asyncio.fixture
async def application_id(client: AsyncClient, candidate_token: str, job_id: str) -> str:
    resp = await client.post("/applications/", data={"job_id": job_id},
        files={"resume": ("resume.pdf", b"fake resume content", "application/pdf")},
        headers={"Authorization": f"Bearer {candidate_token}"})
    return resp.json()["id"]
