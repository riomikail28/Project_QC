#!/bin/sh
set -eu

# Verify latest DB dump and WAL tarball integrity
BACKUP_DIR="${BACKUP_DIR:-/backups}"
echo "Looking for latest dump in $BACKUP_DIR"
LATEST_DUMP=$(ls -1t $BACKUP_DIR/qc_db_*.dump.gz 2>/dev/null | head -n1 || true)
if [ -n "$LATEST_DUMP" ]; then
  echo "Verifying dump: $LATEST_DUMP"
  if pg_restore -l "$LATEST_DUMP" >/dev/null 2>&1; then
    echo "Dump OK"
  else
    echo "Dump verification FAILED" >&2
    exit 2
  fi
else
  echo "No dump found to verify"
fi

LATEST_WAL=$(ls -1t $BACKUP_DIR/wal_*.tar.gz 2>/dev/null | head -n1 || true)
if [ -n "$LATEST_WAL" ]; then
  echo "Verifying WAL tar: $LATEST_WAL"
  if tar -tzf "$LATEST_WAL" >/dev/null 2>&1; then
    echo "WAL tar OK"
  else
    echo "WAL tar verification FAILED" >&2
    exit 3
  fi
else
  echo "No WAL tar found to verify"
fi

echo "Verification completed"
exit 0
