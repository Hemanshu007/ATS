# ATS — Applicant Tracking System

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![CI](https://github.com/Hemanshu007/ATS/actions/workflows/ci.yml/badge.svg)
![Tests](https://img.shields.io/badge/Tests-129%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

A full-stack AI-powered Applicant Tracking System — job posting, applications with resume upload, LLM-based resume parsing, pgvector semantic candidate-job matching, a grounded conversational search over candidates, and a complete hiring pipeline with a React frontend for both candidates and recruiters.

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│    React     │────▶│   FastAPI   │────▶│  PostgreSQL  │◀────│  Celery      │
│  (frontend/) │     │  (async)    │     │  + pgvector  │     │  Worker      │
│  Port 5173   │     │  Port 8000  │     │  Port 5432   │     │              │
└──────────────┘     └──────┬──────┘     └──────────────┘     └──────┬───────┘
                             │                                       │
                             │            ┌──────────────┐           │
                             └───────────▶│    Redis     │◀──────────┘
                                          │  Port 6379   │
                                          └──────────────┘

Pipeline:
  Resume Upload → LLM Extraction → Embedding Generation → pgvector Storage
  Job Posting   → Embedding Generation → pgvector Storage
  Search Query  → Embedding → Similarity Search → LLM Grounded Explanation
```

## Features

- **JWT Authentication** — register/login for candidates and recruiters with role-based access, refresh token rotation
- **Job Management** — CRUD for job postings with soft delete, status control, filtering, and pagination
- **Application Pipeline** — apply with resume upload, enforced status-transition state machine, full history audit trail
- **Interview Scheduling** — schedule rounds, record outcomes, interviewer double-booking detection, timezone-aware datetimes
- **Internal Notes** — recruiter notes on applications
- **Recruiter & Candidate Dashboards** — pipeline summaries, job/application counts, profile management
- **AI Resume Parsing** — LLM-powered structured extraction (skills, experience, education, summary) via Celery
- **Semantic Matching** — pgvector cosine-similarity search between candidate resumes and job descriptions
- **Conversational RAG Search** — natural language queries over candidates with grounded, evidence-cited explanations (hallucination-controlled)
- **React Frontend** — role-based candidate/recruiter UIs, JWT refresh-on-401, toast notifications, responsive down to 375px
- **Background Processing** — Celery tasks for email notifications, resume/embedding processing, and stale-application sweeps
- **Rate Limiting** — per-endpoint request throttling
- **Job Caching** — Redis-backed job listing cache with write-path invalidation
- **Structured Logging** — JSON logs via structlog with ISO timestamps
- **Load Tested** — cold vs warm cache benchmarks, 42% P50 latency improvement on cached reads
- **CI** — GitHub Actions running the full backend test suite against real Postgres + pgvector and Redis

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI (async) + Python 3.11 |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS |
| Frontend Data Layer | TanStack Query + Axios |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| Task Queue | Celery + Redis |
| LLM Provider | Gemini 2.5 Flash (configurable: OpenAI / Gemini) |
| Embeddings | Gemini embedding-001 (3072-dim vectors) |
| Vector Search | pgvector cosine similarity |
| Dependency Mgmt | uv (backend), npm (frontend) |
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

# 2. Start all backend services
docker compose up --build -d

# 3. Run migrations
docker compose exec api uv run alembic upgrade head

# 4. Seed test data
docker compose exec api uv run python scripts/seed.py

# 5. Backend available at http://localhost:8000
#    Docs at http://localhost:8000/docs

# 6. Start the frontend
cd frontend
cp .env.example .env
npm install
npm run dev
# Frontend available at http://localhost:5173
```

## Local Development (without Docker)

```bash
# Backend
uv sync
uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload

# Terminal 2 — Celery worker (emails + resume processing)
uv run celery -A app.core.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat (scheduled tasks)
uv run celery -A app.core.celery_app beat --loglevel=info

# Terminal 4 — Frontend
cd frontend && npm install && npm run dev
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
| GET | /jobs/ | - | List open jobs (cached, filterable) |
| GET | /jobs/{id} | - | Get job details |
| PATCH | /jobs/{id}/status | Recruiter | Close/open job |
| DELETE | /jobs/{id} | Recruiter | Soft delete job |
| POST | /applications/ | Candidate | Apply with resume upload |
| GET | /applications/job/{id} | Recruiter | List applications for job (filterable) |
| GET | /applications/me | Candidate | My applications |
| GET | /applications/{id} | Bearer | Application detail (owner-scoped) |
| PATCH | /applications/{id}/status | Recruiter | Update application status |
| GET | /applications/{id}/history | Recruiter | Status change history |
| GET | /applications/{id}/resume | Recruiter | Download resume (local file or S3 presigned URL) |
| POST | /applications/{id}/notes | Recruiter | Add internal note |
| GET | /applications/{id}/notes | Recruiter | List notes |
| POST | /interviews/ | Recruiter | Schedule interview round |
| GET | /interviews/application/{id} | Recruiter | List interview rounds |
| GET | /interviews/{id} | Recruiter | Interview round detail |
| PATCH | /interviews/{id}/outcome | Recruiter | Record outcome |
| DELETE | /interviews/{id} | Recruiter | Cancel interview round |
| GET | /jobs/{id}/matches | Recruiter | Semantic candidate matching (pgvector) |
| POST | /jobs/{id}/search | Recruiter | Conversational RAG search |
| GET | /documents/me | Candidate | List my uploaded documents |
| DELETE | /documents/{id} | Candidate | Delete a document |
| GET | /companies/ | - | List companies |
| GET | /companies/{id} | - | Company detail + open job count |
| GET | /companies/{id}/jobs | - | Open jobs for a company |
| GET | /companies/me | Recruiter | My company detail |
| PATCH | /companies/me | Recruiter | Update my company |
| GET | /recruiters/me/dashboard | Recruiter | Pipeline summary |
| GET | /recruiters/me/jobs | Recruiter | My jobs with application counts |
| GET | /candidates/me/profile | Candidate | My profile |
| PATCH | /candidates/me/profile | Candidate | Update my profile |
| GET | /candidates/me/dashboard | Candidate | Application summary |
| GET | /health | - | Health check |
| GET | /ready | - | Readiness check (DB connectivity) |

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
├── models/               # SQLAlchemy models
├── schemas/              # Pydantic request/response schemas
├── routers/               # API route handlers
├── services/
│   ├── storage.py       # Local filesystem resume storage
│   ├── s3.py             # AWS S3 resume storage
│   ├── email.py          # Email sending via SMTP/SES
│   ├── llm_extraction.py # LLM-powered resume parsing
│   ├── llm_search.py     # Conversational RAG search with grounding
│   └── embeddings.py     # Vector embedding generation
└── tasks/                 # Celery tasks (email, resume processing, scheduled)

frontend/
├── src/
│   ├── api/               # Typed request modules per backend router + Axios client
│   ├── context/            # AuthContext, ToastContext
│   ├── components/         # Shared UI (Navbar, ProtectedRoute, layouts, StatusBadge)
│   ├── pages/
│   │   ├── candidate/       # Apply, applications, profile, dashboard
│   │   └── recruiter/       # Dashboard, jobs, applications, matches/search
│   └── types/              # Domain types mirroring backend Pydantic schemas
└── ...
```

## Running Tests

```bash
uv run pytest -v
```

129 tests covering auth, CRUD, applications, interviews, matching, search, caching, and error handling.

## Load Testing

```bash
# Cold cache benchmark
uv run locust -f loadtests/locust_cold.py --host http://localhost:8000

# Warm cache benchmark
uv run locust -f loadtests/locust_warm.py --host http://localhost:8000

# Write-heavy benchmark
uv run locust -f loadtests/locust_write.py --host http://localhost:8000
```

## Deployment

Docker images are provided for `api`, `worker`, and `beat` services. See [docker-compose.yml](docker-compose.yml) for local orchestration; the same images are designed to run on AWS ECS Fargate with RDS (Postgres + pgvector), ElastiCache (Redis), and S3 for resume storage.

## License

MIT — see [LICENSE](LICENSE).
