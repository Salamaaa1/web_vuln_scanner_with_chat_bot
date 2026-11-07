#!/usr/bin/env bash
# =============================================================================
# Update the API to the latest code on GitHub.
#
#   bash ~/app/deploy/aws/update.sh
#
# Never asks for your keys: it reuses the settings saved by setup.sh
# (~/app/deploy/aws/.env, which git never touches).
# =============================================================================
set -euo pipefail

main() {
  local dir
  dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$dir"

  if [ ! -f .env ]; then
    echo "No saved settings found. Run setup.sh once first:" >&2
    echo "  bash $dir/setup.sh" >&2
    exit 1
  fi

  echo "==> Getting the latest code"
  git -C "$dir/../.." pull --ff-only

  echo "==> Sizing nuclei to this server's RAM"
  bash "$dir/tune.sh"

  echo "==> Rebuilding and restarting the API (your settings are kept)"
  sudo docker compose up -d --build

  local domain
  domain="$(sed -n "s/^API_DOMAIN='\{0,1\}\([^']*\)'\{0,1\}$/\1/p" .env | tail -n 1)"
  echo "==> Waiting for https://$domain ..."
  for _ in $(seq 1 36); do
    if curl -fsS "https://$domain/" >/dev/null 2>&1; then
      echo "Updated. API is online: https://$domain"
      exit 0
    fi
    sleep 5
  done
  echo "The API isn't answering yet. Check the logs with:" >&2
  echo "  cd $dir && sudo docker compose logs --tail 50" >&2
  exit 1
}

# Everything runs from main(), which bash reads completely before starting.
# That keeps this script safe even when 'git pull' replaces this file mid-run.
main "$@"
