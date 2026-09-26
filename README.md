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
| `content/schema/` | JSON Schema for `syllabus.json`, Question Bank files and `changelog.json`, generated from `api/app/content/format.py` ([format notes](docs/content-format.md)) |
| `content/<stack>/<version>/` | One Syllabus version: `syllabus.json`, `questions/<lesson-id>.json` and `changelog.json` |
| `.claude/skills/update-syllabus/` | The `/update-syllabus` command that writes a new Syllabus version ([below](#update-a-syllabus)) |
| `api/` | FastAPI app, SQLAlchemy models, Alembic migrations, and the `content-check`, `content-diff`, `content-import`, `content-new-version` and `content-schema` commands |
| `web/` | Next.js 16 front end (App Router, server components) |
| `render.yaml`, `api/Dockerfile` | Deployment ([docs/deploy.md](docs/deploy.md)) |

## Run it locally

Needs [uv](https://docs.astral.sh/uv/), Node 24, Docker, and a Clerk development instance for sign-in (set it up as in [docs/deploy.md](docs/deploy.md#sign-in-with-clerk), including the `email` session-token claim).

1. Put the Clerk keys in `web/.env.local`, which git ignores:

   ```bash
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   ```

   Then set the API's sign-in settings in the shell that starts it:

   ```bash
   export CLERK_ISSUER=https://your-app-12.clerk.accounts.dev   # the Frontend API URL
   export CLERK_AUTHORIZED_PARTIES=http://localhost:3000
   export ADMIN_EMAILS=you@example.com                          # you, the Admin
   ```

2. Start Postgres 16. It listens on host port **5433**, so it doesn't clash with a local Postgres on 5432.

   ```bash
   docker compose up -d db
   ```

3. Create the tables, then import every committed Stack version. The import is idempotent, so running it again changes nothing.

   ```bash
   cd api && uv run alembic upgrade head && uv run content-import ../content
   ```

4. Start the API on http://localhost:8000:

   ```bash
   cd api && uv run uvicorn app.main:app --reload --port 8000
   ```

5. Start the web app:

   ```bash
   cd web && npm install && npm run dev
   ```

Open http://localhost:3000 and sign in with the `ADMIN_EMAILS` address. A first sign-in goes to onboarding: pick an Active Stack and confirm your time zone. **Settings** switches the Active Stack or time zone later, and for the Admin it links to **Invitations**, where you invite other people.

| Variable | Read by | Default |
|---|---|---|
| `API_URL` | web | `http://localhost:8000` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | web | none. Without them `npm run dev` uses Clerk's keyless mode, but the API then needs that temporary instance's `CLERK_ISSUER` |
| `DATABASE_URL` | API | `postgresql+psycopg://learning:learning@localhost:5433/learning` |
| `CLERK_ISSUER`, `CLERK_JWKS_URL`, `CLERK_AUTHORIZED_PARTIES`, `ADMIN_EMAILS` | API | none. Without `CLERK_ISSUER`, everything except `/health` answers 503 ([details](docs/deploy.md#environment-variables)) |
| `ANTHROPIC_API_KEY` | API | none. Grades written answers with Claude Haiku 4.5 (`api/app/grading.py`). Without it the app runs, but submitting a quiz with a written answer answers 503 `grading_failed` and the Learner can resubmit later. Never commit it |

`.claude/launch.json` starts both servers with the local database, the API URL and `CLERK_AUTHORIZED_PARTIES`. The API still needs `CLERK_ISSUER` and `ADMIN_EMAILS` from the environment it is started in.

## Update a Syllabus

In Claude Code, from the repo root:

```
/update-syllabus agentic-ai-engineer
```

It researches the Stack's field against primary sources and writes a new version folder, `content/<stack>/<version>/`. The folder holds the Syllabus, a Question Bank for every Lesson, and a `changelog.json` of what changed, why, and its sources. It passes the content check before the command finishes. A Stack that doesn't exist yet is created. Review the folder, then commit and import it. The steps are in [.claude/skills/update-syllabus/SKILL.md](.claude/skills/update-syllabus/SKILL.md).

It never asks questions, so it also runs headless, for example from a scheduled task:

```bash
claude -p "/update-syllabus agentic-ai-engineer" \
  --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Bash(uv run --project api content-new-version *),Bash(uv run --project api content-diff *),Bash(uv run --project api content-check *),Bash(git status *),Bash(git log *),Bash(grep *)"
```

- `acceptEdits` lets it write files. `--allowedTools` lets it research, start sub-agents and run the content tools, and nothing else.
- Anything else it tries is denied, not prompted for.
- Add `--max-budget-usd 20` (or whatever you choose) to cap what one run costs.
- **In Git Bash**, put `MSYS_NO_PATHCONV=1` in front. Otherwise Git Bash rewrites `/update-syllabus` into a Windows path and the command never runs. PowerShell, macOS and Linux shells don't need it.

The content tools it relies on also work by hand, from the repo root:

| Command | What it does |
|---|---|
| `uv run --project api content-new-version <stack>` | Copies the newest version to a new folder named for today, and starts its changelog. Items you don't touch keep their IDs because they are copies. |
| `uv run --project api content-diff [<old>] <new>` | Lists what was added, changed and removed, by permanent ID, per kind. With one folder, it compares with the version before it. `--json` for scripts. |

## Checks

```bash
cd api && uv run content-check ../content
```

This checks every Stack version against the format and the Question Bank rules:
- 8–12 Questions per bank, and at least 2 per Concept;
- enough Questions for a Lesson Quiz;
- permanent IDs unique across every kind of item, and never reused as another kind in a later version;
- every Material reference exists;
- a version that follows another has a changelog that lists every added, changed and removed Lesson, with sources.

Each error names the file and the item, such as the Question. Add `--links` to also check that every Material URL loads. The rules are in [docs/content-format.md](docs/content-format.md).

**Pre-commit hook.** Install it once, from the repo root:

```bash
uvx pre-commit install
```

This needs only `uv`, with no global install and no scripts. From then on, a commit that touches `content/` (or the check itself) runs `uv run --project api content-check content`. The commit is refused if there are errors. To run the hook by hand, use `uvx pre-commit run --all-files`.

**In CI**, the `content` job runs the same command on every committed Stack version, so a pull request with invalid content fails. The **Content links** workflow runs `--links`:
- weekly, and on demand from the Actions tab, over every Stack version;
- on pull requests that touch `content/`, over only the Stack versions they change.

A dead link is an error. A site that refuses automated requests is only a warning.

```bash
cd api && uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy
```

The API tests use a real Postgres: the compose `db` service by default, or `TEST_DATABASE_URL`. They create a `learning_test` database and build it from the migrations. They need no Clerk account: they sign their own session tokens with a locally generated RSA key (`api/tests/conftest.py`). After changing the format models, run `uv run content-schema` to regenerate `content/schema/`. After changing the database models, run `uv run alembic revision --autogenerate -m "..."`. A test fails if either one is forgotten.

```bash
cd web && npm run typecheck && npm run lint && npm test && npm run build
```

CI runs all of these on every pull request, with Postgres as a service container.
