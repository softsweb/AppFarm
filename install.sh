#!/usr/bin/env bash
set -euo pipefail

# AppFarm server bootstrap - Debian / Ubuntu.
#
# Two jobs:
#   1. Make sure Docker Engine + the Compose plugin are present (installs them if
#      they are not - e.g. a bare VPS). If your provider already ships Docker
#      (Hostinger's "Ubuntu 24 + Docker" template does), this step is skipped.
#   2. Apply the one host tweak AppFarm actually needs: Docker Engine 29+ raised
#      its minimum API version, and Traefik's bundled client negotiates an older
#      one and gets rejected - so Traefik cannot read container labels and no app
#      subdomain routes. Pinning DOCKER_MIN_API_VERSION=1.24 fixes it.
#
# Traefik and everything else ship inside docker-compose.yml, so this is all the
# host setup you need. Safe to re-run.

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root:  sudo ./install.sh"
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  echo "==> Docker already installed: $(docker --version)"
else
  echo "==> Installing Docker"
  apt-get update -y
  apt-get install -y ca-certificates curl
  curl -fsSL https://get.docker.com | sh
fi

systemctl enable --now docker >/dev/null 2>&1 || true

# The one fix AppFarm needs so Traefik (older client) can talk to Docker 29+.
COMPAT=/etc/systemd/system/docker.service.d/api-compat.conf
DESIRED=$'[Service]\nEnvironment=DOCKER_MIN_API_VERSION=1.24\n'
if [ -f "$COMPAT" ] && [ "$(cat "$COMPAT")" = "$DESIRED" ]; then
  echo "==> Docker API compatibility already enabled (DOCKER_MIN_API_VERSION=1.24)"
else
  echo "==> Enabling Docker API compatibility (DOCKER_MIN_API_VERSION=1.24)"
  mkdir -p /etc/systemd/system/docker.service.d
  printf '%s' "$DESIRED" > "$COMPAT"
  systemctl daemon-reload
  systemctl restart docker
fi

echo
echo "==> Docker:  $(docker --version)"
echo "==> Compose: $(docker compose version)"

cat <<'EOF'

✅ Host ready. Docker is up and Traefik is bundled - no extra setup needed.

Next steps (run from this directory):
  1. cp .env.example .env
  2. nano .env          # set DOMAIN, ACME_EMAIL, CLAUDE_CODE_OAUTH_TOKEN
  3. docker compose up -d --build
  4. open https://<your-domain>

To test WITHOUT spending Claude credits first:
  - set APPFARM_FAKE_BUILD=1 in .env, then:
  - docker compose exec control python -m appfarm.cli build-now
EOF
