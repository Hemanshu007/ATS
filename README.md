# ATS - Applicant Tracking System

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-128%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

An AI-powered Applicant Tracking System backend — job posting, applications, resume parsing via LLM, semantic candidate-job matching with pgvector, conversational search, and a full hiring pipeline API.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   FastAPI    │────▶│  PostgreSQL  │◀────│  Celery      │
│  (async)     │     │  + pgvector  │     │  Worker      │
│  Port 8000   │     │  Port 5432   │     │              │
└──────┬───────┘     └──────────────┘     └──────┬───────┘
       │                                          │
       │          ┌──────────────┐                │
       └─────────▶│    Redis     │◀───────────────┘
                  │  Port 6379   │
                  └──────────────┘

Pipeline:
  Resume Upload → LLM Extraction → Embedding Generation → pgvector Storage
  Job Posting   → Embedding Generation → pgvector Storage
  Search Query  → Embedding → Similarity Search → LLM Grounded Explanation
```

## Features

- **JWT Authentication** — register/login for candidates and recruiters with role-based access
- **Job Management** — CRUD for job postings with soft delete and status control
- **Application Pipeline** — apply with resume upload, status tracking with full history audit trail
- **Interview Scheduling** — schedule rounds, record outcomes with timezone-aware datetimes
- **Internal Notes** — recruiter notes on applications
- **AI Resume Parsing** — LLM-powered structured extraction (skills, experience, education, summary)
- **Semantic Matching** — pgvector similarity search between candidate resumes and job descriptions
- **Conversational RAG Search** — natural language queries over candidates with grounded, cited explanations (hallucination-controlled)
- **Background Processing** — Celery tasks for email notifications, resume processing, and stale-application sweeps
- **Rate Limiting** — per-endpoint request throttling
- **Job Caching** — Redis-backed job listing cache with 60s TTL
- **Structured Logging** — JSON logs via structlog with ISO timestamps
- **Load Tested** — cold vs warm cache benchmarks, 42% P50 improvement on cached reads

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) + Python 3.11 |
| Database | PostgreSQL 18 + pgvector |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Task Queue | Celery + Redis |
| LLM Provider | Gemini 2.5 Flash (configurable: OpenAI / Gemini) |
| Embeddings | Gemini embedding-001 (3072-dim vectors) |
| Vector Search | pgvector cosine similarity |
| Dependency Mgmt | uv |
| Orchestration | Docker Compose |
| Load Testing | Locust |
| Logging | structlog |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Hemanshu007/ATS.git
cd ATS
cp .env.example .env
# Edit .env with your API keys and database credentials

# 2. Start all services
docker compose up --build -d

# 3. Run migrations
docker compose exec api uv run alembic upgrade head

# 4. Seed test data
docker compose exec api uv run python scripts/seed.py

# 5. API available at http://localhost:8000
#    Docs at http://localhost:8000/docs
```

## Local Development

```bash
# Install dependencies
uv sync

# Start PostgreSQL and Redis separately, then:
uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload

# Terminal 2 — Celery worker (emails + resume processing)
uv run celery -A app.core.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat (scheduled tasks)
uv run celery -A app.core.celery_app beat --loglevel=info
```

## Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Recruiter | alice@techcorp.com | recruiter123 |
| Candidate | hemanshu@gmail.com | candidate123 |

Company: **TechCorp** (Technology, Bangalore)

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | - | Register candidate or recruiter |
| POST | /auth/login | - | Login, get JWT |
| POST | /auth/refresh | - | Refresh access token |
| GET | /auth/me | Bearer | Get current user + profile |
| POST | /jobs/ | Recruiter | Create job posting |
| GET | /jobs/ | - | List open jobs (cached) |
| GET | /jobs/{id} | - | Get job details |
| PATCH | /jobs/{id}/status | Recruiter | Close/open job |
| DELETE | /jobs/{id} | Recruiter | Soft delete job |
| POST | /applications/ | Candidate | Apply with resume upload |
| GET | /applications/job/{id} | Recruiter | List applications for job |
| GET | /applications/me | Candidate | My applications |
| PATCH | /applications/{id}/status | Recruiter | Update application status |
| GET | /applications/{id}/history | Recruiter | Status change history |
| POST | /applications/{id}/notes | Recruiter | Add internal note |
| GET | /applications/{id}/notes | Recruiter | List notes |
| POST | /interviews/ | Recruiter | Schedule interview round |
| GET | /interviews/application/{id} | Recruiter | List interview rounds |
| PATCH | /interviews/{id}/outcome | Recruiter | Record outcome |
| POST | /jobs/{id}/matches | Recruiter | Semantic candidate matching |
| POST | /jobs/{id}/search | Recruiter | Conversational RAG search |
| GET | /health | - | Health check |

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── database.py          # Async engine + session
├── core/
│   ├── config.py        # Settings via pydantic-settings
│   ├── security.py      # JWT + password hashing
│   ├── dependencies.py  # Auth guards (get_current_user/recruiter/candidate)
│   ├── redis_client.py  # Async Redis client
│   ├── celery_app.py    # Celery app + beat schedule
│   └── cache.py         # Job listing cache helpers
├── models/              # SQLAlchemy models (10+ tables)
├── schemas/             # Pydantic request/response schemas
├── routers/             # API route handlers
├── services/
│   ├── storage.py       # Local filesystem resume storage
│   ├── email.py         # Email sending via SMTP
│   ├── llm_extraction.py# LLM-powered resume parsing
│   ├── llm_search.py    # Conversational RAG search with grounding
│   └── embeddings.py    # Vector embedding generation
└── tasks/               # Celery tasks (email, resume processing, scheduled)
```

## Running Tests

```bash
uv run pytest -v
```

128 tests covering auth, CRUD, applications, interviews, matching, search, caching, and error handling.

## Load Testing

```bash
# Cold cache benchmark
uv run locust -f loadtests/locust_cold.py --host http://localhost:8000

# Warm cache benchmark
uv run locust -f loadtests/locust_warm.py --host http://localhost:8000

# Write-heavy benchmark
uv run locust -f loadtests/locust_write.py --host http://localhost:8000
```

## License

MIT
