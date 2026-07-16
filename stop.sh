#!/usr/bin/env bash
# Stop and remove all Auto-Pentest containers (data volumes are kept).
docker rm -f pentest-frontend pentest-scanner pentest-redis pentest-mongodb 2>/dev/null || true
echo "Auto-Pentest stopped. (Data volumes pentest_mongo_data / pentest_redis_data are preserved.)"
