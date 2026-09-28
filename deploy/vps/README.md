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
`OWN_GRADING_KEY_REQUIRED=false` (a Learner without a key of their own is graded with the
Admin's saved key; no `CLAUDE_CODE_OAUTH_TOKEN` is set, so the server's Claude Code never
grades),
`PUBLIC_HOST=prep.chickenkiller.com` and `POSTGRES_PASSWORD`. The Clerk instance is a development one, which works on any domain
(docs/deploy.md).

## Updating

Every push to `main` deploys itself. [`CI`](../../.github/workflows/ci.yml) runs the API,
content and web checks. When it passes on a push to `main`,
[`Deploy`](../../.github/workflows/deploy.yml) streams that commit's `git archive` over SSH
to the VPS. To redeploy `main` without a push, run **Deploy** by hand from the Actions tab.

On the VPS, the deploy key can run only [`ic-deploy.sh`](ic-deploy.sh), installed as
`/usr/local/bin/ic-deploy`. It unpacks the archive over `/opt/interview-cracker`, which keeps
`deploy/vps/.env`. Then it rebuilds, waits for healthy containers and writes the commit to
`DEPLOYED_COMMIT`. Each deploy reinstalls the script from the commit it deploys. The key's line
in `~ubuntu/.ssh/authorized_keys` is:

```
restrict,command="/usr/local/bin/ic-deploy" ssh-ed25519 AAAA… github-actions-deploy@interview-cracker
```

The private key is the repository secret `VPS_DEPLOY_KEY`. To replace the key, generate a
new pair, swap that line, and update the secret.

New content under `content/` is imported when the API restarts.

To deploy by hand from a checkout, with an SSH key that is allowed a shell:

```bash
git archive --format=tar.gz HEAD | ssh ubuntu@146.235.21.90 "SSH_ORIGINAL_COMMAND='deploy $(git rev-parse HEAD)' ic-deploy"
```

## Useful commands

```bash
C="sudo docker compose -f /opt/interview-cracker/deploy/vps/docker-compose.yml --env-file /opt/interview-cracker/deploy/vps/.env"
$C ps
$C logs -f api
$C exec db pg_dump -U learning -d learning -Fc > backup.dump
```
