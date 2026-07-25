# ATS - Applicant Tracking System

Backend API for managing the hiring pipeline — job posting, applications, status tracking, interviews, and notes.

## Tech Stack

- **FastAPI** (async) + Python 3.11
- **PostgreSQL 15** via SQLAlchemy 2.0 async + asyncpg
- **Alembic** for migrations
- **JWT** auth (python-jose + passlib/bcrypt)
- **Local filesystem** for resume storage
- **Celery + Redis** for email notifications (durable, retriable)
- **uv** for dependency management
- **Docker Compose** for orchestration

## Quick Start

```bash
# 1. Copy env file and configure
cp .env.example .env
# Edit .env with your Fastmail SMTP credentials

# 2. Start services (includes API, DB, Redis, and Celery worker)
docker compose up --build -d

# 3. Run migrations (inside api container)
docker compose exec api uv run alembic upgrade head

# 4. Seed test data
docker compose exec api uv run python seed.py

# 5. API available at http://localhost:8001
# 6. Docs at http://localhost:8001/docs
```

## Test Credentials

After running the seed script:

| Role | Email | Password |
|------|-------|----------|
| Recruiter | alice@techcorp.com | recruiter123 |
| Candidate | hemanshu@gmail.com | candidate123 |

Company: **TechCorp** (Technology, Bangalore)

## Local Development (without Docker)

```bash
# Install dependencies
uv sync

# Start PostgreSQL and Redis separately, then:
uv run alembic upgrade head
uv run python seed.py
uv run uvicorn app.main:app --reload

# In a separate terminal, start the Celery worker for email sending:
uv run celery -A app.core.celery_app worker --loglevel=info
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | - | Register candidate or recruiter |
| POST | /auth/login | - | Login, get JWT |
| GET | /auth/me | Bearer | Get current user + profile |
| POST | /jobs/ | Recruiter | Create job posting |
| GET | /jobs/ | - | List open jobs |
| GET | /jobs/{id} | - | Get job details |
| PATCH | /jobs/{id}/status | Recruiter | Close/open job |
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

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── database.py          # Async engine + session
├── core/
│   ├── config.py        # Settings via pydantic-settings
│   ├── security.py      # JWT + password hashing
│   └── dependencies.py  # Auth guards (get_current_user/recruiter/candidate)
├── models/              # SQLAlchemy models (10 tables)
├── schemas/             # Pydantic request/response schemas
├── routers/             # API route handlers
└── services/            # Storage + email services
```
