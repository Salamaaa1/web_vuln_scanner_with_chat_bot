#!/usr/bin/env bash
# ============================================================
#  Auto-Pentest — one-click launcher (Linux / macOS)
#  Pulls the 4 images from Docker Hub, wires them together,
#  and starts the whole stack:  ./run.sh
#  Requires Docker installed and running.
# ============================================================
set -e

# Always work from the folder this script lives in, so ".env" is found.
cd "$(dirname "$0")"

NET=pentest-net
MONGO=salamaaa11/auto-pentest-mongodb:latest
REDIS=salamaaa11/auto-pentest-redis:latest
SCANNER=salamaaa11/auto-pentest-scanner:latest
FRONTEND=salamaaa11/auto-pentest-frontend:latest

echo "[1/6] Pulling images from Docker Hub..."
for img in "$MONGO" "$REDIS" "$SCANNER" "$FRONTEND"; do docker pull "$img"; done

echo "[2/6] Creating private network..."
docker network create "$NET" 2>/dev/null || true

echo "[3/6] Removing any previous containers..."
docker rm -f pentest-mongodb pentest-redis pentest-scanner pentest-frontend 2>/dev/null || true

echo "[4/6] Starting MongoDB and Redis..."
docker run -d --name pentest-mongodb --network "$NET" -p 27017:27017 \
  -v pentest_mongo_data:/data/db --restart unless-stopped "$MONGO"
docker run -d --name pentest-redis --network "$NET" -p 6379:6379 \
  -v pentest_redis_data:/data --restart unless-stopped "$REDIS"

echo "[5/6] Waiting for MongoDB to be ready..."
until docker exec pentest-mongodb mongosh --quiet --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
  sleep 2
done

# Load the AI key from .env if present (optional — enables the Assistant IA tab).
if [ -f .env ]; then set -a; . ./.env; set +a; fi

echo "[6/6] Starting scanner API and frontend..."
docker run -d --name pentest-scanner --network "$NET" -p 8000:8000 \
  -e MONGODB_URL=mongodb://pentest-mongodb:27017 \
  -e DATABASE_NAME=scanner \
  -e REDIS_URL=redis://pentest-redis:6379 \
  -e NMAP_TOP_PORTS=1000 -e NMAP_TIMING=-T4 \
  -e NVIDIA_API_KEY="${NVIDIA_API_KEY:-}" \
  -e NVIDIA_MODEL="${NVIDIA_MODEL:-deepseek-ai/deepseek-v4-flash}" \
  --restart unless-stopped "$SCANNER"
docker run -d --name pentest-frontend --network "$NET" -p 3000:3000 \
  --restart unless-stopped "$FRONTEND"

echo ""
echo "============================================================"
echo "  Auto-Pentest is starting up."
echo "  Open http://localhost:3000 in your browser."
echo "  (The scanner API is on http://localhost:8000)"
echo "  To stop everything, run ./stop.sh"
echo "============================================================"
