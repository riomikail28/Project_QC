#!/bin/sh
#set -eux

# Lightweight smoke test wrapper: fetch latest backup with wal-g and verify files exist
WALG_BIN=${WALG_BIN:-/usr/local/bin/wal-g}
TARGET_DIR=${1:-/tmp/qc_restore_test}

if [ ! -x "$WALG_BIN" ]; then
  echo "wal-g not found at $WALG_BIN" >&2
  exit 2
fi

mkdir -p "$TARGET_DIR"

echo "Fetching latest backup into $TARGET_DIR"
$WALG_BIN backup-fetch "$TARGET_DIR" LATEST

if [ -n "$(ls -A "$TARGET_DIR")" ]; then
  echo "Restore smoke test: files present in $TARGET_DIR"
  exit 0
else
  echo "Restore smoke test FAILED: no files in $TARGET_DIR" >&2
  exit 3
fi
