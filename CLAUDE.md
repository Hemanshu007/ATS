# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An async FastAPI backend for an Applicant Tracking System (ATS): job postings, applications with resume upload, interview scheduling, LLM-based resume parsing, and pgvector semantic search with a grounded conversational RAG endpoint. Solo project by Hemanshu007.

## Commands

```bash
# Install deps (uv-managed project)
uv sync

# Run the API locally (needs Postgres+pgvector and Redis running separately)
uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload

# Celery worker (emails + resume/embedding processing) and beat (stale-application sweep)
uv run celery -A app.core.celery_app worker --loglevel=info
uv run celery -A app.core.celery_app beat --loglevel=info

# Full stack via Docker (api + db + redis + worker + beat)
docker compose up --build -d
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python scripts/seed.py

# Tests (SQLite in-memory, no external services needed — see tests/conftest.py)
uv run pytest -v
uv run pytest tests/test_matching.py -v          # single file
uv run pytest tests/test_matching.py::test_name -v  # single test

# New migration after editing app/models/*
uv run alembic revision --autogenerate -m "description"

# Load tests (require a running server)
uv run locust -f loadtests/locust_cold.py --host http://localhost:8000
```

CI (`.github/workflows/ci.yml`) runs `uv run pytest -v --tb=short` against real Postgres+pgvector and Redis service containers on every push/PR to `main`.

## Architecture

**Request flow:** `routers/` (HTTP layer, auth deps, validation) → `services/` (business logic, external calls) / direct SQLAlchemy queries → `models/` (SQLAlchemy ORM) → Postgres. `schemas/` hold Pydantic request/response models, kept separate from ORM models.

**Auth:** JWT access+refresh tokens (`app/core/security.py`, PyJWT). Three-tier dependency chain in `app/core/dependencies.py`: `get_current_user` (validates JWT, loads `User`) → `get_current_recruiter` / `get_current_candidate` (checks `role`, loads the role-specific profile row `Recruiter`/`Candidate`). Routers depend on whichever tier they need; a `Recruiter`/`Candidate` dependency implies an authenticated `User` of that role.

**Domain model:** `User` (auth/role) 1:1 with either `Recruiter` (belongs to a `Company`) or `Candidate`. `Job` belongs to a `Recruiter`/`Company`. `Application` links a `Candidate` to a `Job` via a uploaded `Document` (resume), with a `UniqueConstraint(job_id, candidate_id)` preventing duplicate applications — enforced at the DB level, not just app logic. `ApplicationStatusHistory` is an append-only audit trail written every time `Application.current_status` changes. `InterviewRound` and `ApplicationNote` hang off `Application`.

**Status state machine:** `app/core/constants.py` (`ALLOWED_STATUS_TRANSITIONS`) defines the legal graph (applied → screening → interview → offer → hired, with rejected as a sink from several states). `app/services/application_service.py::validate_status_transition` is the single enforcement point — always route status changes through it rather than mutating `current_status` directly.

**Application creation is transactional and lock-guarded** (`app/routers/applications.py::apply`): row-locks the `Job` with `SELECT ... FOR UPDATE` (skipped on SQLite, which doesn't support it — see the `dialect != "sqlite"` check), inserts `Document` + `Application` + `ApplicationStatusHistory` in one transaction, and relies on the DB unique constraint (caught as `IntegrityError`) as the authoritative duplicate-application guard rather than a pre-check query.

**RAG / matching pipeline** (the core "AI" feature):
1. Resume uploaded → `Application` created synchronously → Celery task `process_resume` dispatched (`app/tasks/resume_processing_tasks.py`).
2. Task extracts PDF text (`pypdf`), calls `llm_extraction.extract_resume_data` for structured fields (skills, work history, education — provider-agnostic, Gemini or OpenAI per `LLM_PROVIDER`), then `embeddings.generate_embedding` on a skills+work-history string, storing both `parsed_data` (JSON) and `embedding` (pgvector) on `Document`.
3. Job descriptions get embedded the same way via `generate_job_embedding`.
4. `GET /jobs/{id}/matches` — pure pgvector cosine-similarity ranking, no LLM call, advisory-only.
5. `POST /jobs/{id}/search` — embeds the recruiter's NL query, retrieves top-k `Document`s by similarity, then calls `llm_search.generate_search_explanation` with a strict grounding system prompt (`SYSTEM_PROMPT`/`GROUNDING_PROMPT` in `app/services/llm_search.py`) that forbids fabricating anything not in `parsed_data` and requires near-verbatim `supporting_evidence`. Neither matching endpoint writes to `Application.current_status` — both are read-only/advisory.

Every LLM/embedding integration (`llm_extraction.py`, `llm_search.py`, `embeddings.py`) follows the same provider-switch pattern: `if settings.LLM_PROVIDER == "gemini": ... else: ...` with lazy `from google import genai` / `from openai import AsyncOpenAI` imports inside the function. Add new providers by extending this branch in all three files consistently.

**Caching:** `app/core/cache.py` caches `GET /jobs/` listings in Redis for 60s, keyed by page/page_size/filters plus a version counter (`_cache_version_key`) that's incremented on any job mutation to invalidate all cached pages at once, rather than deleting individual keys.

**Background jobs:** Celery + Redis broker (`app/core/celery_app.py`). Task queues: resume/embedding processing, transactional email (`app/tasks/email_tasks.py`), and a daily beat job (`flag_stale_applications`, 02:00 UTC) that flags applications idle past `STALE_APPLICATION_DAYS`. Sync Celery tasks bridge into async code via a fresh `asyncio` event loop per task (see `process_resume`) — follow this pattern for new async-calling tasks rather than making the task itself `async def`.

**Storage:** `app/services/storage.py` (local filesystem, `UPLOAD_DIR`) and `app/services/s3.py` (AWS S3 via boto3, presigned download URLs) both exist; check `app/core/config.py` (`AWS_*`/`S3_BUCKET_NAME` vs `UPLOAD_DIR`) and call sites to see which is active for a given deployment — the S3 path is the newer/AWS-deployment-ready one per recent commits.

**Config:** all settings are centralized in `app/core/config.py` (`pydantic-settings`, loads `.env`). Add new env vars there, not as scattered `os.environ` reads. `.env.example` documents every variable.

**Tests:** `tests/conftest.py` overrides `get_db` to use SQLite (`aiosqlite`) instead of Postgres, and monkey-patches pgvector `Vector` columns to plain `JSON` for SQLite compatibility — so pgvector-specific SQL (e.g. `.cosine_distance()`) is only truly exercised in CI/Docker against real Postgres, not in local `pytest` runs. Rate limiting is disabled in tests (`limiter.enabled = False`). Fixtures (`recruiter_token`, `candidate_token`, `job_id`, `application_id`) build up test data through the real API rather than direct DB inserts — follow that pattern for new tests.

## Notes

- A `requirements.md` spec under `help/.cursor/.kiro/specs/` (leftover from another tool's session) describes a broader set of enhancements (pagination envelopes, soft-delete on jobs, company/recruiter/candidate dashboard endpoints, S3 migration script, etc.). Some of this is already implemented (pagination via `app/schemas/pagination.py`, S3 service, resume file validation); treat it as a design reference, not a changelog of what's done — verify against actual code before assuming a requirement is met.
- Test/seed credentials are in `README.md` (`scripts/seed.py` creates a TechCorp recruiter + candidate) — dev-only, not real secrets.
