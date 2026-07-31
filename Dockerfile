FROM python:3.11-slim

RUN adduser --disabled-password --no-create-home appuser

ENV HOME=/app \
    UV_CACHE_DIR=/app/.cache/uv

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --no-dev --no-install-project

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/

# Pre-create the uploads dir so the named volume mounted here at runtime inherits
# appuser ownership on first use (an empty bind point would default to root).
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
