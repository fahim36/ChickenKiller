# The API image. Build from the repo root so the committed content/ is included:
#   docker build -f api/Dockerfile -t learning-api .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/api/.venv/bin:$PATH"

WORKDIR /app/api

# Dependencies first, so code changes don't reinstall them.
COPY api/pyproject.toml api/uv.lock api/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY api/ ./
COPY content/ /app/content/
RUN uv sync --locked --no-dev

EXPOSE 8000
# release.sh migrates the database and imports content/ (idempotent), then the server starts.
CMD ["sh", "-c", "sh ./release.sh && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
