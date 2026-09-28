# The API image for the VPS: api/Dockerfile plus the Claude Code CLI, so written answers are
# graded on this host (docs/adr/0006). The CLI signs in with CLAUDE_CODE_OAUTH_TOKEN.
# Build context: the repo root.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://claude.ai/install.sh | bash \
    && ln -s /root/.local/bin/claude /usr/local/bin/claude \
    && claude --version

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/api/.venv/bin:$PATH"

WORKDIR /app/api

COPY api/pyproject.toml api/uv.lock api/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY api/ ./
COPY content/ /app/content/
RUN uv sync --locked --no-dev

EXPOSE 8000
# release.sh migrates the database and imports content/ (idempotent), then the server starts.
CMD ["sh", "-c", "sh ./release.sh && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
