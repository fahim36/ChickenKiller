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

You need a GitHub account with access to `fahim36/InterviewCrackerAssistant`. No other secrets are needed until sign-in (#3) adds Clerk keys.

1. Merge the branch you want live into `main` and push it.
2. Sign in at https://dashboard.render.com with GitHub. Creating the account and authorising Render's GitHub app is a step only a person can do.
3. Choose **New → Blueprint**, pick the `InterviewCrackerAssistant` repository, keep the branch as `main`, and click **Apply**.
   - Render reads `render.yaml` and creates `learning-db`, `learning-api` and `learning-web`.
   - It asks for the one value marked `sync: false`, which is `API_URL`. Enter a placeholder such as `https://example.com` for now.
4. Wait for `learning-api` to go live. Its log should show:
   ```
   Running upgrade  -> 0001, content tables: ...
   agentic-ai-engineer v2026-09-26: imported (current)
   Uvicorn running on http://0.0.0.0:...
   ```
5. Copy the API's public URL from the top of its Render page, such as `https://learning-api-abcd.onrender.com`. Check that `<that URL>/health` returns `{"status":"ok"}`.
6. Open `learning-web` → **Environment**. Set `API_URL` to the API URL from step 5, with no trailing slash, then choose **Save, rebuild and deploy**.
7. Open the web service's public URL, such as `https://learning-web-abcd.onrender.com`. You should see the Stack list. Open **Agentic AI Engineer** and then a Lesson: its topics and its Materials with type labels are shown. **This URL is the app's public URL.**

After that, every push to `main` redeploys both services, and Render's auto-deploy is on by default.

## Deploying the web app to Vercel instead (optional)

Vercel is a good fit for Next.js if you prefer it. The API and database stay on Render.

1. At https://vercel.com/new, import the repository and set **Root Directory** to `web`. Vercel detects Next.js by itself.
2. Add the environment variable `API_URL` with the Render API URL from step 5 above.
3. Deploy, then remove the `learning-web` service from `render.yaml` (or suspend it) so you aren't running two front ends.

## Checking a deploy

```bash
curl https://<api-url>/health
curl https://<api-url>/stacks/agentic-ai-engineer/lessons/w01-l01
```

## Running the production image locally

```bash
docker compose up -d db
docker build -f api/Dockerfile -t learning-api .
docker run --rm --network jobhunt_default -p 8000:8000 \
  -e DATABASE_URL=postgresql://learning:learning@db:5432/learning learning-api
```

The compose network is named after the checkout folder: `jobhunt_default` for a folder called `Job Hunt`. `docker network ls` lists the names.
