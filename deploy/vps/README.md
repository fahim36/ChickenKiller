# Running the app on the VPS

The whole app runs on the Oracle Cloud VPS (`146.235.21.90`, Ubuntu 24.04, ARM) at
**https://prep.chickenkiller.com**, from `/opt/interview-cracker`.

| Piece | Where | Notes |
|---|---|---|
| Postgres 16 | container `db` | Data in the `interview-cracker_db-data` volume. Not published. |
| API | container `api`, `127.0.0.1:8100` | [`api.Dockerfile`](api.Dockerfile): `api/Dockerfile` plus the Claude Code CLI, so written answers are graded here (ADR-0006). Each start runs `release.sh`: migrations, then an idempotent content import. |
| Web | container `web`, `127.0.0.1:3100` | `API_URL` is `http://api:8000`; `MCP_PUBLIC_URL` is `https://prep.chickenkiller.com/mcp/`. |
| nginx | host, [`nginx.conf`](nginx.conf) → `/etc/nginx/sites-available/interview-cracker` | `/mcp/` goes to the API and everything else to the web app. |
| TLS | Let's Encrypt, `certbot` webroot `/var/www/letsencrypt` | The existing `certbot.timer` renews it, and the `reload-nginx.sh` deploy hook reloads nginx. |

**How HTTPS gets in.** OpenVPN owns tcp/443 on this host (`/etc/openvpn/server/server.conf`,
`proto tcp`), and `port-share 127.0.0.1 8443` hands every non-VPN connection to nginx on
loopback 8443. There nginx picks the site by SNI, next to `feed.jumpingcrab.com`. Port 80
answers only certificate renewals and redirects to HTTPS. No new firewall or Oracle ingress
rule was needed, because 80 and 443 were already open.

**Settings** live in `deploy/vps/.env` on the VPS (mode 600, never committed):
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_ISSUER`, `ADMIN_EMAILS`,
`LLM_KEY_SECRET`, `OPEN_SIGNUP=true` (anyone can sign up),
`OWN_GRADING_KEY_REQUIRED=true` (each Learner grades with their own NVIDIA key; no
`CLAUDE_CODE_OAUTH_TOKEN` is set, so the server's Claude Code can't grade),
`PUBLIC_HOST=prep.chickenkiller.com` and `POSTGRES_PASSWORD`. The Clerk instance is a development one, which works on any domain
(docs/deploy.md).

## Updating

Copy the new code to `/opt/interview-cracker` with LF line endings (a Windows checkout has CRLF,
which breaks `release.sh`), then rebuild:

```bash
cd /opt/interview-cracker
sudo docker compose -f deploy/vps/docker-compose.yml --env-file deploy/vps/.env up -d --build
```

New content under `content/` is imported when the API restarts.

## Useful commands

```bash
C="sudo docker compose -f /opt/interview-cracker/deploy/vps/docker-compose.yml --env-file /opt/interview-cracker/deploy/vps/.env"
$C ps
$C logs -f api
$C exec db pg_dump -U learning -d learning -Fc > backup.dump
```
