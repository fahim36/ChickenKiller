#!/usr/bin/env bash
# Deploys one commit of the app on the VPS. It is the forced command of the GitHub Actions deploy
# key (deploy/vps/README.md), so that key can run nothing else:
#
#   git archive --format=tar.gz <sha> | ssh ubuntu@<vps> deploy <sha>
#
# It unpacks the archive over /opt/interview-cracker (deploy/vps/.env is not in the repo, so it
# is kept), rebuilds and restarts the containers, waits until they are healthy, and records the
# commit in DEPLOYED_COMMIT. Installed as /usr/local/bin/ic-deploy; each deploy reinstalls it
# from the commit it deploys.
set -euo pipefail

APP=/opt/interview-cracker
COMPOSE=(sudo docker compose -f "$APP/deploy/vps/docker-compose.yml" --env-file "$APP/deploy/vps/.env")

read -r verb sha extra <<<"${SSH_ORIGINAL_COMMAND:-}" || true
if [[ "${verb:-}" != deploy || ! "${sha:-}" =~ ^[0-9a-f]{40}$ || -n "${extra:-}" ]]; then
  echo "usage: deploy <40-character commit sha>, with the commit's tar.gz on stdin" >&2
  exit 2
fi

exec 9>/tmp/ic-deploy.lock
flock -n 9 || { echo "Another deploy is running." >&2; exit 75; }

archive=$(mktemp)
trap 'rm -f "$archive"' EXIT
head -c 200M >"$archive"
gzip -t "$archive"

echo "Unpacking $sha"
cd "$APP"
sudo tar xzf "$archive" --no-same-owner
# A Windows checkout's archive has CRLF line endings, which break release.sh.
tar tzf "$archive" | grep -v '/$' | xargs -r -d '\n' sudo grep -Il $'\r' |
  xargs -r -d '\n' sudo sed -i 's/\r$//' || true

echo "Building and starting the containers"
"${COMPOSE[@]}" up -d --build --wait --wait-timeout 900

echo "$sha" | sudo tee "$APP/DEPLOYED_COMMIT" >/dev/null
sudo install -m 755 "$APP/deploy/vps/ic-deploy.sh" /usr/local/bin/ic-deploy
sudo docker image prune -f >/dev/null
"${COMPOSE[@]}" ps
echo "Deployed $sha"
