# Developing InterviewCrackerAssistant

How the app is built, run and checked. How to use it is in the [README](../README.md).

Daily interview-prep games, modeled on LinkedIn Games. Every Stack (such as Agentic AI Engineer) releases one numbered Daily Challenge a day: three Questions, the same for everyone, released at 00:00 UTC. Playing it keeps your Streak going, and a Result Card shows how you did. Past Challenges stay playable in the Archive, and Catch-up lists the ones you missed. Next to the Challenges, each Stack has a researched Syllabus of Weekly Lessons. Each Lesson ends with a quiz you must pass before the next one unlocks. An optional Review brings Missed Questions back until they stick.

Claude Code does the content work. In the Admin's terminal it keeps the Syllabus current and writes the Upcoming Challenges as reviewed, version-numbered content files. On the API's machine it grades written answers.

- Glossary: [CONTEXT.md](../CONTEXT.md)
- Decisions: [docs/adr/](adr/)
- Where Version 1 stands (progress, known gaps, to do): [docs/status.md](status.md)
- Plan: [docs/build-plan.md](build-plan.md) (milestones, tests and demos) and [docs/implementation-order.md](implementation-order.md) (ticket order)

```mermaid
graph LR
  CC["Claude Code<br/>(Admin terminal)"] -->|"writes + commits"| C["content/stack/version"]
  C -->|"content-check"| C
  C -->|"content-import"| DB[("Postgres")]
  API["FastAPI (api/)"] --> DB
  WEB["Next.js (web/)"] --> API
  API -->|"grades written answers<br/>with claude -p"| CL["Claude Code CLI<br/>(on the API machine)"]
```

## Repo layout

| Path | What's there |
|---|---|
| `content/schema/` | JSON Schema for `syllabus.json`, Question Bank files, `changelog.json` and Daily Challenge files, generated from `api/app/content/format.py` ([format notes](content-format.md)) |
| `content/<stack>/<version>/` | One Syllabus version: `syllabus.json` and `changelog.json` |
| `content/<stack>/question-bank/` | The Stack's one Question Bank, append-only, with each Question's Sources ([ADR-0004](adr/0004-append-only-question-bank-with-sources.md)) |
| `content/<stack>/challenges/` | The Stack's launch Day and its Daily Challenges, one file per Day, frozen once released |
| `.claude/skills/update-syllabus/` | The `/update-syllabus` command that writes a new Syllabus version ([below](#update-a-syllabus)) |
| `.claude/skills/write-challenges/` | The `/write-challenges` command that writes the next Upcoming Challenges ([below](#write-upcoming-challenges)) |
| `api/` | FastAPI app, SQLAlchemy models, Alembic migrations, and the `content-check`, `content-diff`, `content-import`, `content-migrate-bank`, `content-new-version` and `content-schema` commands |
| `web/` | Next.js 16 front end (App Router, server components) |
| `run-app.cmd`, `docker-compose.yml`, `web/Dockerfile`, `.env.example` | Running the whole app on this machine ([below](#run-it-locally)) |
| `render.yaml`, `api/Dockerfile` | Deployment ([docs/deploy.md](deploy.md)) |

## Run it locally

### One command (Windows)

Needs Docker Desktop (running), [uv](https://docs.astral.sh/uv/), and [Claude Code](https://claude.com/claude-code) installed and signed in (it grades written answers).

1. **Set up Clerk once.** Create a Clerk development instance for sign-in, as in [docs/deploy.md](deploy.md#sign-in-with-clerk).

2. **Fill in `.env.local`.** Copy `.env.example` to `.env.local` at the repo root; git ignores it. Fill in the two Clerk keys, `CLERK_ISSUER` (the instance's Frontend API URL) and `ADMIN_EMAILS`, the address you sign in with. That account is the Admin.

3. **Start it:**

   ```bash
   run-app.cmd
   ```

   It does four things:
   - rebuilds the Docker images;
   - starts Postgres (host port 5433) and the web app (http://localhost:3000) in Docker;
   - migrates the database and imports `content/`;
   - runs the API on this machine at http://localhost:8000.

   The API runs outside Docker so it can use your signed-in Claude Code ([ADR-0006](adr/0006-grading-runs-the-claude-code-cli.md)). Once it prints "Application startup complete", open http://localhost:3000. Ctrl+C stops the API. `run-app.cmd stop` stops the containers.

Run it again after pulling changes. It rebuilds the images and imports any new content.

| Problem | What to do |
|---|---|
| "Port 8000 is already in use" | An API from an earlier run is still going. Stop it, or set `API_PORT` in `.env.local`. |
| "Your sign-in couldn't be verified" | Sign out and in again. If it keeps happening, check the Clerk setup in [docs/deploy.md](deploy.md#sign-in-with-clerk). |
| "You haven't been invited yet" | Sign in with the address in `ADMIN_EMAILS`, or fix `ADMIN_EMAILS` and run `run-app.cmd` again. |
| `content-import` says "already imported with different content" | The local database holds content from an older layout. If it has no progress you want to keep, recreate it: `docker compose exec db psql -U learning -d postgres -c "drop database learning with (force)" -c "create database learning owner learning"`. |

### By hand

Needs [uv](https://docs.astral.sh/uv/), Node 24, Docker, and a Clerk development instance for sign-in (set it up as in [docs/deploy.md](deploy.md#sign-in-with-clerk)).

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

Open http://localhost:3000 and sign in with the `ADMIN_EMAILS` address. A first sign-in goes to onboarding: pick one or more Stacks to study, and land on the home screen with a card for each. **Settings** activates or deactivates Stacks later (a deactivated Stack keeps its progress), and for the Admin it links to **Invitations**, where you invite other people.

| Variable | Read by | Default |
|---|---|---|
| `API_URL` | web | `http://localhost:8000` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | web | none. Without them `npm run dev` uses Clerk's keyless mode, but the API then needs that temporary instance's `CLERK_ISSUER` |
| `DATABASE_URL` | API | `postgresql+psycopg://learning:learning@localhost:5433/learning` |
| `CLERK_ISSUER`, `CLERK_JWKS_URL`, `CLERK_AUTHORIZED_PARTIES`, `ADMIN_EMAILS` | API | none. Without `CLERK_ISSUER`, everything except `/health` answers 503 ([details](deploy.md#environment-variables)) |
| `OPEN_SIGNUP` | API | off. `true` lets anyone who signs up become a Learner, with no invitation |
| `OWN_GRADING_KEY_REQUIRED` | API | off. `true` grades each Learner's written answers only with their own saved key, never the Admin's key or the server's Claude Code. The Admin is graded as before |
| `CLAUDE_BIN` | API | `claude` on the PATH (on Windows, `claude.exe`). Written answers are graded by running Claude Code headless with Claude Haiku 4.5 (`api/app/grading.py`, ADR-0006), so Claude Code must be installed and signed in on the machine running the API. Without it the app runs, but submitting a quiz with a written answer answers 503 `grading_failed` and the Learner can resubmit later |

`.claude/launch.json` starts both servers with the local database, the API URL and `CLERK_AUTHORIZED_PARTIES`. The API still needs `CLERK_ISSUER` and `ADMIN_EMAILS` from the environment it is started in.

## Update a Syllabus

In Claude Code, from the repo root:

```
/update-syllabus agentic-ai-engineer
```

It researches the Stack's field against primary sources and writes a new Syllabus version, `content/<stack>/<version>/`, with a `changelog.json` of what changed in the Syllabus, why, and its sources. In the Stack's Question Bank, `content/<stack>/question-bank/`, it adds new Questions (each with the Sources it fetched), retires out-of-date ones with a reason and a replacement, and re-tags Questions to another Lesson; it never edits or deletes a committed Question. It reads the whole bank first, and the whole Stack passes the content check before it finishes. When its research finds nothing to change, it writes nothing and reports "no change". A Stack that doesn't exist yet is created. Review the new version and the bank's diff, then commit and import them. The steps are in [.claude/skills/update-syllabus/SKILL.md](../.claude/skills/update-syllabus/SKILL.md).

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
| `uv run --project api content-diff [<old>] <new>` | Lists what the Syllabus added, changed and removed, by permanent ID, per kind. With one folder, it compares with the version before it. Then lists the Questions the Question Bank added, retired and re-tagged since git `HEAD` (`--baseline <ref>` for another). `--json` for scripts. |

## Write Upcoming Challenges

In Claude Code, from the repo root:

```
/write-challenges agentic-ai-engineer 7
```

It reads the Stack's whole Question Bank, researches the field, and writes the next 7 Upcoming Challenges: `content/<stack>/challenges/<number>.json`, each with its number, UTC date and three Questions (two multiple choice, one written). New Questions go into the Question Bank with Sources fetched in the run, preferring Concepts the bank doesn't test yet. The first run for a Stack writes its launch Day (tomorrow, UTC). It passes the content check before it finishes. Review the files, then commit and import them. The steps are in [.claude/skills/write-challenges/SKILL.md](../.claude/skills/write-challenges/SKILL.md).

A Challenge can be edited until its Day begins; from 00:00 UTC on its Day it is released and frozen, and the content check refuses any change. A Day with no Challenge written has no Challenge, so keep a few Days ahead: the content check and the Admin's **Upcoming Challenges** page (Settings → Admin) show "Challenges written through <date> (<n> Days left)" per Stack, and warn when fewer than three Days are left.

It never asks questions, so it also runs headless, for example from a scheduled task:

```bash
claude -p "/write-challenges agentic-ai-engineer 7" \
  --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Bash(uv run --project api content-check *),Bash(git status *),Bash(git log *),Bash(grep *),Bash(date *)"
```

The flags work as for `/update-syllabus` above, including `MSYS_NO_PATHCONV=1` in Git Bash.

## Checks

```bash
cd api && uv run content-check ../content
```

This checks every Stack version against the format and the Question Bank rules:
- at least 8 Questions per Lesson that aren't retired, enough for a Lesson Quiz, and at least 2 per Concept;
- every Question has Sources, and the Question Bank is append-only against git: never edited or deleted, only retired or re-tagged;
- permanent IDs unique across every kind of item, and never reused as another kind in a later version;
- every Material reference exists;
- a version that follows another has a changelog that lists every added, changed and removed Lesson, with sources;
- Daily Challenges numbered and dated from the launch, with two multiple-choice Questions and one written, and never changed once their Day has begun.

Each error names the file and the item, such as the Question. Add `--links` to also check that every Material URL loads. The rules are in [docs/content-format.md](content-format.md).

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
