#!/usr/bin/env bash
# =============================================================================
# One-command setup of the scanner API on a fresh Ubuntu EC2 server.
#
#   git clone https://github.com/Salamaaa1/web_vuln_scanner_with_chat_bot.git ~/app
#   bash ~/app/deploy/aws/setup.sh
#
# Run it once. To update later, use update.sh (never asks for your keys).
# Running setup.sh again is also safe: it keeps your saved settings.
# See DEPLOY.md for the full walkthrough.
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/Salamaaa1/web_vuln_scanner_with_chat_bot.git"
APP_DIR="${APP_DIR:-$HOME/app}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# Read a value from the keyboard (works even when this script is piped).
ask() {
  local prompt=$1 secret=${2:-} optional=${3:-} val="" src=/dev/stdin
  if ( : </dev/tty ) 2>/dev/null; then src=/dev/tty; fi
  while :; do
    if [ -n "$secret" ]; then
      read -r -s -p "$prompt: " val <"$src" || true; echo >&2
    else
      read -r -p "$prompt: " val <"$src" || true
    fi
    val="${val#"${val%%[![:space:]]*}"}"; val="${val%"${val##*[![:space:]]}"}"   # trim
    if [ -n "$val" ] || [ -n "$optional" ]; then break; fi
    echo "  (required, please paste a value)" >&2
  done
  printf '%s' "$val"
}

say "[1/6] Adding 2 GB of swap memory (helps the small server during scans)"
if ! sudo swapon --show | grep -q '/swapfile'; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
echo "ok"

say "[2/6] Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker >/dev/null 2>&1 || true
sudo docker compose version

say "[3/6] Getting the latest code"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/deploy/aws"

say "[4/6] Finding this server's public address"
TOKEN=$(curl -fsS -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
IP=$(curl -fsS -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/public-ipv4")
API_DOMAIN="${IP//./-}.sslip.io"
echo "public IP: $IP  ->  https://$API_DOMAIN"

say "[5/6] Settings"
if [ ! -f .env ]; then
  echo "Paste each value from your Notepad, then press Enter."
  echo "(Secret values are hidden while you paste - that's normal.)"
  MONGODB_URL=$(ask "MONGODB_URL  (mongodb+srv://...)" secret)
  REDIS_URL=$(ask "REDIS_URL    (rediss://...)" secret)
  NVIDIA_API_KEY=$(ask "NVIDIA_API_KEY (Enter to skip: AI tab disabled)" secret optional)
  umask 077
  cat > .env <<EOF
MONGODB_URL='${MONGODB_URL}'
REDIS_URL='${REDIS_URL}'
NVIDIA_API_KEY='${NVIDIA_API_KEY}'
NVIDIA_MODEL='deepseek-ai/deepseek-v4-flash'
ALLOWED_ORIGINS='*'
EOF
  echo "saved to $APP_DIR/deploy/aws/.env (only readable by you)"
else
  echo "keeping existing settings ($APP_DIR/deploy/aws/.env)"
fi
# The domain follows the server's IP, so refresh it on every run.
sed -i '/^API_DOMAIN=/d' .env
echo "API_DOMAIN='${API_DOMAIN}'" >> .env

say "[6/6] Building and starting the API (first time: about 5-10 minutes)"
sudo docker compose up -d --build

echo
echo "Waiting for the API and its HTTPS certificate..."
for i in $(seq 1 60); do
  if curl -fsS "https://$API_DOMAIN/" >/dev/null 2>&1; then
    echo
    echo "=================================================================="
    echo " API is online:  https://$API_DOMAIN"
    echo " Use this as NEXT_PUBLIC_API_URL on Vercel (see DEPLOY.md)."
    echo "=================================================================="
    exit 0
  fi
  sleep 5
done
echo "The API isn't answering yet. Check the logs with:"
echo "  cd $APP_DIR/deploy/aws && sudo docker compose logs --tail 50"
exit 1
