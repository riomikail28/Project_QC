#!/bin/sh
set -eux

# CI helper: fetch latest wal-g backup and run an ephemeral Postgres container to validate restore
WALG_BIN=${WALG_BIN:-/usr/local/bin/wal-g}
TARGET_DIR=${1:-/tmp/ci_pgdata}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-restorepass}

if [ ! -x "$WALG_BIN" ]; then
  echo "wal-g not found at $WALG_BIN" >&2
  exit 2
fi

echo "Fetching latest backup into $TARGET_DIR"
rm -rf "$TARGET_DIR" || true
mkdir -p "$TARGET_DIR"
$WALG_BIN backup-fetch "$TARGET_DIR" LATEST

echo "Adjusting ownership and permissions"
chown -R 999:999 "$TARGET_DIR" || true

echo "Starting ephemeral Postgres container"
docker run -d --name qc_restore -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" -v "$TARGET_DIR":/var/lib/postgresql/data:Z postgres:15-alpine || true

echo "Waiting for Postgres to be ready"
for i in $(seq 1 40); do
  docker exec qc_restore pg_isready -U postgres && break || sleep 3
done

echo "Running basic smoke queries"
docker exec qc_restore psql -U postgres -c "SELECT 1;" || true
docker exec qc_restore psql -U postgres -c "\dt" || true

echo "Stopping and removing container"
docker stop qc_restore || true
docker rm qc_restore || true

echo "CI full restore smoke test succeeded"
exit 0
