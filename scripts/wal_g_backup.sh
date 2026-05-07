#!/bin/sh
set -eu

# Perform a base backup using wal-g (requires WALG_S3_PREFIX and AWS creds)
WALG_BIN=${WALG_BIN:-/usr/local/bin/wal-g}
if [ ! -x "$WALG_BIN" ]; then
  echo "wal-g not found at $WALG_BIN" >&2
  exit 1
fi

echo "Starting wal-g backup-push of PGDATA"
${WALG_BIN} backup-push /var/lib/postgresql/data
echo "wal-g base backup finished"
