#!/bin/bash
# EC2 user-data bootstrap for a t3.micro (free-tier) demo instance running
# the VenuePass stack via docker-compose. Paste this into the instance's
# "User data" field at launch (Amazon Linux 2023 or Ubuntu 22.04+).
#
# This is the free-tier counterpart to deploy/aws/ec2-user-data.sh — use
# that one instead for a real t3.medium+ deployment. On a t3.micro (1GB
# RAM), ai-service (real InsightFace+EasyOCR+torch inference) genuinely
# does not fit in RAM alone — this script leans on a large swap file as a
# deliberate trade-off (slower, but working) rather than the t3.medium
# script's "swap is just a backstop" stance. See the top of
# docker-compose.yml for the corresponding per-service memory budget.
#
# What it does:
#   1. Installs Docker + the Compose plugin
#   2. Adds a 4GB swap file with swappiness biased toward using it (this
#      instance genuinely needs swap as working memory, not just insurance)
#   3. Clones the repo and starts the stack
#
# Prerequisites before launch:
#   - Attach an instance profile with deploy/aws/s3-iam-policy.json
#   - Security group: 22 (SSH, restricted to your IP), 80/443 (if fronted
#     by a reverse proxy) or 3000/8000 directly, nothing else public
#   - Set REPO_URL and the required .env values below (or SSH in and
#     populate /opt/venuepass/.env manually before `docker compose up`)
#   - Expect the first request to ai-service after a cold start to be slow
#     (models paging in from swap) — this is normal on this instance size,
#     not a bug.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/your-org/pub-entry.git}"
APP_DIR="/opt/venuepass"

# --- Docker ---
if command -v dnf >/dev/null 2>&1; then
  dnf update -y
  dnf install -y docker git
  systemctl enable --now docker
  DOCKER_COMPOSE_PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"
  mkdir -p "$DOCKER_COMPOSE_PLUGIN_DIR"
  curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o "$DOCKER_COMPOSE_PLUGIN_DIR/docker-compose"
  chmod +x "$DOCKER_COMPOSE_PLUGIN_DIR/docker-compose"
else
  apt-get update -y
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

# --- Swap (4GB) — only add it if there's none already ---
if ! swapon --show | grep -q .; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  # Higher than the t3.medium script's swappiness=10 on purpose: on 1GB
  # RAM, ai-service's model weights genuinely live in swap most of the
  # time, not just under memory pressure. Delaying swap here (low
  # swappiness) would just mean the OOM killer fires first instead.
  sysctl -w vm.swappiness=60
  echo 'vm.swappiness=60' >> /etc/sysctl.conf
fi

# --- App ---
mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  # Auto-generate a real SECRET_KEY so the stack isn't left with the
  # placeholder value; POSTGRES_PASSWORD/S3_BUCKET_NAME/SEED_ADMIN_PASSWORD
  # still need editing.
  SECRET_KEY_VALUE=$(openssl rand -hex 32)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY_VALUE}|" .env
  echo "Generated .env from template — edit S3_BUCKET_NAME, POSTGRES_PASSWORD, and SEED_ADMIN_PASSWORD before the stack will be production-ready:"
  echo "  $APP_DIR/.env"
fi

docker compose up -d --build

# --- systemd unit so the stack survives reboots even without a login shell ---
cat > /etc/systemd/system/venuepass.service <<EOF
[Unit]
Description=VenuePass docker-compose stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable venuepass.service
