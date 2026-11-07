#!/usr/bin/env bash
# Lock the API so only your dashboard can call it.
#   bash ~/app/deploy/aws/set-frontend.sh https://your-app.vercel.app
set -euo pipefail
url="${1:?usage: set-frontend.sh https://your-app.vercel.app}"
url="${url%/}"
case "$url" in https://*) ;; *) echo "The URL must start with https://" >&2; exit 1 ;; esac
cd "$(dirname "$0")"
[ -f .env ] || { echo "Run setup.sh first." >&2; exit 1; }
sed -i '/^ALLOWED_ORIGINS=/d' .env
echo "ALLOWED_ORIGINS='${url}'" >> .env
sudo docker compose up -d
echo "Done: the API now only accepts requests from ${url}"
