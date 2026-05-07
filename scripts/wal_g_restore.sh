#!/bin/sh
set -eu

# Restore latest backup using wal-g: fetch latest backup and extract into target dir
WALG_BIN=${WALG_BIN:-/usr/local/bin/wal-g}
TARGET_DIR=${1:-/var/lib/postgresql/data_restored}

if [ ! -x "$WALG_BIN" ]; then
  echo "wal-g not found at $WALG_BIN" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
echo "Fetching latest backup into $TARGET_DIR"
${WALG_BIN} backup-fetch "$TARGET_DIR" LATEST
echo "Restore files fetched. To recover, place data directory and start postgres with recovery.conf or use WAL restore." 
