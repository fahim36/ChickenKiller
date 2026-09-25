# InterviewCrackerAssistant

A self-evaluation app for interview preparation. A Learner picks a Stack, studies a Syllabus of Weekly Lessons, and proves each Lesson with a quiz before the next one unlocks. Daily Review Rounds bring Missed Questions back until they stick. The Syllabus is kept current by Claude Code, which runs in the Admin's terminal and writes reviewed, version-numbered content files.

- Glossary: [CONTEXT.md](CONTEXT.md)
- Decisions: [docs/adr/](docs/adr/)
- Plan: [docs/build-plan.md](docs/build-plan.md) (milestones, tests and demos) and [docs/implementation-order.md](docs/implementation-order.md) (ticket order)

```mermaid
graph LR
  CC[Claude Code<br/>Admin's terminal] -->|writes + commits| C[content/&lt;stack&gt;/&lt;version&gt;/]
  C -->|content-check| C
  C -->|content-import| DB[(Postgres)]
  API[FastAPI · api/] --> DB
  WEB[Next.js · web/] --> API
  API -->|grade written answers| CL[Claude API]
```

## Repo layout

| Path | What's there |
|---|---|
| `content/schema/` | JSON Schema for `syllabus.json` and Question Bank files, generated from `api/app/content/format.py` ([format notes](docs/content-format.md)) |
| `content/<stack>/<version>/` | One Syllabus version: `syllabus.json` plus `questions/<lesson-id>.json` |
| `api/` | FastAPI app, SQLAlchemy models, Alembic migrations, and the `content-check`, `content-import` and `content-schema` commands |
| `web/` | Next.js 16 front end (App Router, server components) |
| `render.yaml`, `api/Dockerfile` | Deployment ([docs/deploy.md](docs/deploy.md)) |

## Run it locally

Needs [uv](https://docs.astral.sh/uv/), Node 24 and Docker.

1. Start Postgres 16. It listens on host port **5433**, so it doesn't clash with a local Postgres on 5432.

   ```bash
   docker compose up -d db
   ```

2. Create the tables, then import every committed Stack version. The import is idempotent, so running it again changes nothing.

   ```bash
   cd api && uv run alembic upgrade head && uv run content-import ../content
   ```

3. Start the API on http://localhost:8000:

   ```bash
   cd api && uv run uvicorn app.main:app --reload --port 8000
   ```

4. Start the web app:

   ```bash
   cd web && npm install && npm run dev
   ```

Open http://localhost:3000. The web app reads the API from `API_URL` (default `http://localhost:8000`). The API reads Postgres from `DATABASE_URL` (default `postgresql+psycopg://learning:learning@localhost:5433/learning`). `.claude/launch.json` starts both servers with those settings.

## Checks

```bash
cd api && uv run content-check ../content
```

This checks every Stack version against the format and the Question Bank rules:
- 8–12 Questions per bank, and at least 2 per Concept;
- enough Questions for a Lesson Quiz;
- unique permanent IDs;
- every Material reference exists.

Add `--links` to also check that every Material URL loads. Install the pre-commit hook once with `uvx pre-commit install`, and a commit with broken content is refused.

```bash
cd api && uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy
```

The API tests use a real Postgres: the compose `db` service by default, or `TEST_DATABASE_URL`. They create a `learning_test` database and build it from the migrations. After changing the format models, run `uv run content-schema` to regenerate `content/schema/`. After changing the database models, run `uv run alembic revision --autogenerate -m "..."`. A test fails if either one is forgotten.

```bash
cd web && npm run typecheck && npm run lint && npm test && npm run build
```

CI runs all of these on every pull request, with Postgres as a service container.
