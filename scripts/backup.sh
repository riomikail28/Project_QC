#!/bin/sh
set -eu

# Backup script with compression and optional presigned URL upload
BACKUP_DIR="${BACKUP_DIR:-/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

OUT_FILE="$BACKUP_DIR/qc_db_$STAMP.dump"
COMPRESSED="$OUT_FILE.gz"

echo "Starting pg_dump to $OUT_FILE"
pg_dump -h ${POSTGRES_HOST:-postgres} -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  --format=custom \
  --file="$OUT_FILE"

echo "Compressing backup to $COMPRESSED"
gzip -9 -c "$OUT_FILE" > "$COMPRESSED"
rm -f "$OUT_FILE"

# Optional: upload to presigned URL (set PRESIGNED_UPLOAD_URL env)
if [ -n "${PRESIGNED_UPLOAD_URL:-}" ]; then
  echo "Uploading $COMPRESSED to PRESIGNED_UPLOAD_URL"
  # Use curl to PUT file to presigned URL
  if curl -s -S -T "$COMPRESSED" "$PRESIGNED_UPLOAD_URL" ; then
    echo "Upload successful"
  else
    echo "Upload failed" >&2
  fi
fi

# Cleanup: keep local backups for RETENTION_DAYS (default 14)
RETENTION_DAYS=${RETENTION_DAYS:-14}
find "$BACKUP_DIR" -type f -name 'qc_db_*.dump.gz' -mtime +${RETENTION_DAYS} -print -delete || true

echo "Backup completed: $COMPRESSED"

# Send success alert if configured
if [ -n "${SLACK_WEBHOOK_URL:-}" ] || [ -n "${PAGERDUTY_INTEGRATION_KEY:-}" ]; then
  python3 -c "
import os, json, http.client, datetime
slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
pagerduty_key = os.environ.get('PAGERDUTY_INTEGRATION_KEY')
message = f'Backup completed successfully: $COMPRESSED'
if slack_webhook:
    payload = {
        'text': '[INFO] QC Backup Success',
        'attachments': [{
            'color': 'good',
            'fields': [{'title': 'Status', 'value': message, 'short': False}],
            'footer': 'QC System',
            'ts': datetime.datetime.now().timestamp()
        }]
    }
    conn = http.client.HTTPSConnection('hooks.slack.com')
    conn.request('POST', slack_webhook, json.dumps(payload), {'Content-Type': 'application/json'})
    conn.getresponse()
    conn.close()
if pagerduty_key:
    # Only send alerts on errors for PagerDuty
    pass
"
fi

# WAL archive upload (tar and upload if PRESIGNED_WAL_URL provided)
WAL_DIR="${WAL_DIR:-/backups/wal}"
if [ -n "${PRESIGNED_WAL_URL:-}" ] && [ -d "$WAL_DIR" ]; then
  WAL_TAR="$BACKUP_DIR/wal_$STAMP.tar.gz"
  echo "Archiving WALs from $WAL_DIR to $WAL_TAR"
  tar -czf "$WAL_TAR" -C "$WAL_DIR" . || true
  if [ -f "$WAL_TAR" ]; then
    echo "Uploading WAL tar to PRESIGNED_WAL_URL"
    if curl -s -S -T "$WAL_TAR" "$PRESIGNED_WAL_URL" ; then
      echo "WAL upload successful"
    else
      echo "WAL upload failed" >&2
    fi
  fi
fi
