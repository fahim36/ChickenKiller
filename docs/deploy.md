# Deploying the Learning App

The app runs as three pieces on [Render](https://render.com), all defined in [`render.yaml`](../render.yaml):

| Piece | What it is | Free plan notes |
|---|---|---|
| `learning-db` | Managed Postgres 16 | A free database expires after 30 days. Upgrade it, or re-create it and redeploy. The import puts all content back. |
| `learning-api` | The FastAPI app, built from [`api/Dockerfile`](../api/Dockerfile) | It sleeps after 15 idle minutes, and the first request then takes roughly 30–60 s. |
| `learning-web` | The Next.js app in `web/` | It sleeps the same way. |

**Release step.** Every time the API starts, it runs [`api/release.sh`](../api/release.sh):

1. `alembic upgrade head` brings the database schema up to date.
2. `content-import /app/content` imports every committed Stack version.

The import is idempotent. A version that is already imported is left unchanged, and a new version becomes the current Syllabus. Deploying content therefore means committing it to `content/` and pushing.

## One-time setup (a human does this)

You need a GitHub account with access to `fahim36/InterviewCrackerAssistant`, and a Clerk application set up as in [Sign-in with Clerk](#sign-in-with-clerk) below.

1. Merge the branch you want live into `main` and push it.
2. Sign in at https://dashboard.render.com with GitHub. Creating the account and authorising Render's GitHub app is a step only a person can do.
3. Choose **New → Blueprint**, pick the `InterviewCrackerAssistant` repository, keep the branch as `main`, and click **Apply**.
   - Render reads `render.yaml` and creates `learning-db`, `learning-api` and `learning-web`.
   - It asks for each value marked `sync: false`:

     | Service | Variable | Value |
     |---|---|---|
     | `learning-api` | `CLERK_ISSUER` | The Clerk Frontend API URL |
     | `learning-api` | `CLERK_AUTHORIZED_PARTIES` | A placeholder such as `https://example.com` for now |
     | `learning-api` | `ADMIN_EMAILS` | Your own email address |
     | `learning-web` | `API_URL` | A placeholder such as `https://example.com` for now |
     | `learning-web` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | The Clerk publishable key (`pk_...`) |
     | `learning-web` | `CLERK_SECRET_KEY` | The Clerk secret key (`sk_...`) |
4. Wait for `learning-api` to go live. Its log should show:
   ```
   Running upgrade  -> 0001, content tables: ...
   agentic-ai-engineer v2026-09-26: imported (current)
   Uvicorn running on http://0.0.0.0:...
   ```
5. Copy the API's public URL from the top of its Render page, such as `https://learning-api-abcd.onrender.com`. Check that `<that URL>/health` returns `{"status":"ok"}`.
6. Open `learning-web` → **Environment**. Set `API_URL` to the API URL from step 5, with no trailing slash, then choose **Save, rebuild and deploy**.
7. Copy the web service's public URL, such as `https://learning-web-abcd.onrender.com`. **This URL is the app's public URL.** Open `learning-api` → **Environment**, set `CLERK_AUTHORIZED_PARTIES` to it (no trailing slash), and save.
8. Open the public URL. You are sent to the sign-in page. Sign in with the address in `ADMIN_EMAILS`, and you should see the Stack list with an **Invitations** link. Open **Agentic AI Engineer** and then a Lesson: its topics and its Materials with type labels are shown.

After that, every push to `main` redeploys both services, and Render's auto-deploy is on by default.

## Sign-in with Clerk

Sign-in is handed to [Clerk](https://clerk.com) (ADR-0002). The app keeps its own invitation list, and that list decides who gets in:

- The web app shows Clerk's sign-in and sign-up pages. Anyone can create a Clerk account there.
- The API checks the Clerk session token on every request except `/health`. A person gets in only if their email address was invited by the Admin, or is listed in `ADMIN_EMAILS`. Their Learner is created on their first sign-in.
- Anyone else sees the "You haven't been invited yet" page, and the API answers them with 403.

The app sends no invitation email. After inviting someone on the **Invitations** screen, send them the app's URL yourself.

### One-time setup (a human does this)

Creating the Clerk account is a step only a person can do.

1. Sign up at https://dashboard.clerk.com and create an application named, for example, "Interview Cracker".
   - Choose **Email** and **Google** as the sign-in options.
   - The new application starts as a **development instance**. It works on any URL, including `onrender.com`, and is enough for an invite-only app. It shows a small "Development mode" badge. A production instance needs a domain you own and your own Google OAuth credentials.
2. Under **User & authentication**, check that **Email address** is on and required, with verification by email code, and that **Google** is on under **SSO connections**.
3. Add the email to the session token. Open **Sessions → Customize session token**, and set it to:
   ```json
   {
     "email": "{{user.primary_email_address}}"
   }
   ```
   Save. The API refuses tokens that have no `email` claim. Clerk session tokens don't include the email by default, and the claim saves a call to Clerk's Backend API on every request.
4. Open **API keys** and note three values:
   - the **Publishable key** (`pk_test_...`), for `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` on the web app;
   - the **Secret key** (`sk_test_...`), for `CLERK_SECRET_KEY` on the web app. Keep it secret, and never commit it;
   - the **Frontend API URL**, such as `https://your-app-12.clerk.accounts.dev`, for `CLERK_ISSUER` on the API.
5. Leave **Restrictions → Sign-up mode** as **Public**. In **Restricted** mode Clerk would refuse invited people too, because they're invited in this app, not in Clerk.

### Environment variables

| Service | Variable | What it is |
|---|---|---|
| API | `CLERK_ISSUER` | The Frontend API URL. Tokens must have this `iss`. The signing keys are read from `<CLERK_ISSUER>/.well-known/jwks.json` and cached. Without it, every endpoint except `/health` answers 503. |
| API | `CLERK_JWKS_URL` | Optional. Overrides the JWKS URL above. |
| API | `CLERK_AUTHORIZED_PARTIES` | The web app's origins, comma-separated, such as `https://learning-web-abcd.onrender.com`. Tokens must have one of them as `azp`. If it is empty, any `azp` is accepted, so always set it in production. |
| API | `ADMIN_EMAILS` | The Admin's email address. Comma-separate several. The Admin is always let in and is the only one who can open **Invitations**. |
| Web | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | The publishable key. It is built into the page, so set it before the build. |
| Web | `CLERK_SECRET_KEY` | The secret key. |

If you use Vercel for the web app, set the two web variables there as well.

## Grading written answers

The API grades each written answer against its Model Answer by running the Claude Code CLI headless on its own machine (ADR-0006), so grading uses the Claude plan signed in there. The model (Claude Haiku 4.5), the prompt, the command's flags and the limits are constants in `api/app/grading.py`. The command is:

```
claude -p --model claude-haiku-4-5 --effort low --system-prompt <grading rules> --output-format json --json-schema <{passed, feedback}> --tools "" --setting-sources "" --safe-mode --strict-mcp-config --disable-slash-commands --no-session-persistence --max-budget-usd 0.05
```

It runs in an empty temporary directory with the prompt on stdin, and is stopped after 45 s.

**On Render (or any host without Claude Code) written answers can't be graded.** The app still starts and multiple-choice answers still score, but a submission with a written answer answers 503 `grading_failed`: nothing is recorded, and the Learner can submit again. Grading works when the API runs on a machine where Claude Code is installed and signed in, such as running it locally.

| Service | Variable | What it is |
|---|---|---|
| API | `CLAUDE_BIN` | Optional. The Claude Code CLI to run. By default `claude` on the PATH; on Windows only a native `claude.exe` is used (an npm `claude.cmd` shim is refused). |

Each grading call is logged on one line, such as `INFO: app.grading grading_call {"model": "claude-haiku-4-5", "input_tokens": 1643, "output_tokens": 562, "cost_usd": "0.004453", "duration_ms": 7015, ...}`. The cost is what the CLI reports at list price; on a Claude plan it counts toward the plan's usage limits rather than being billed. A timeout, a CLI error (such as not being signed in) or an unusable reply is logged as `grading_failed`.

## Deploying the web app to Vercel instead (optional)

Vercel is a good fit for Next.js if you prefer it. The API and database stay on Render.

1. At https://vercel.com/new, import the repository and set **Root Directory** to `web`. Vercel detects Next.js by itself.
2. Add the environment variables `API_URL` (the Render API URL from step 5 above), `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`. Add the Vercel URL to the API's `CLERK_AUTHORIZED_PARTIES`.
3. Deploy, then remove the `learning-web` service from `render.yaml` (or suspend it) so you aren't running two front ends.

## Checking a deploy

```bash
curl https://<api-url>/health                   # {"status":"ok"}
curl -i https://<api-url>/stacks                # 401 "Sign in first." (503 if CLERK_ISSUER is missing)
```

Everything except `/health` needs a session token, so check the rest through the web app.

## Running the production image locally

```bash
docker compose up -d db
docker build -f api/Dockerfile -t learning-api .
docker run --rm --network jobhunt_default -p 8000:8000 \
  -e DATABASE_URL=postgresql://learning:learning@db:5432/learning \
  -e CLERK_ISSUER=https://your-app-12.clerk.accounts.dev \
  -e CLERK_AUTHORIZED_PARTIES=http://localhost:3000 -e ADMIN_EMAILS=you@example.com \
  learning-api
```

The compose network is named after the checkout folder: `jobhunt_default` for a folder called `Job Hunt`. `docker network ls` lists the names.
