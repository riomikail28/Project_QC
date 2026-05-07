"""Example Celery tasks used by the QC system."""
from .celery_app import celery_app
from celery.utils.log import get_task_logger
from celery import shared_task
import os
from celery.exceptions import Retry
import time
from prometheus_client import Counter
from backend.workers.idempotency import idempotent_task

logger = get_task_logger(__name__)

# Prometheus metrics for Celery tasks
TASK_SUCCESS = Counter('qc_celery_task_success_total', 'Total successful celery tasks', ['task'])
TASK_FAILURE = Counter('qc_celery_task_failure_total', 'Total failed celery tasks', ['task'])
TASK_RETRY = Counter('qc_celery_task_retries_total', 'Total celery task retries', ['task'])


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
@idempotent_task(lambda args, kwargs: f"send_finding:{args[0].get('id') if args and args[0] else 'unknown'}", ttl=60)
def send_finding_async(self, finding):
    """Send a finding to external service (Google Sheets) with retries and metrics.

    finding: dict-like payload
    """
    import logging
    from backend.notifications.alert_service import alert_service
    
    task_name = 'send_finding_async'
    backup_logger = logging.getLogger('qc.workers.send_finding')
    try:
        # Import inside task to avoid heavy imports at module load
        from integrations.google_sheets_service import send_finding
        send_finding(finding)
        logger.info("send_finding_async: success for %s", finding.get('id'))
        TASK_SUCCESS.labels(task=task_name).inc()
    except Exception as exc:
        failed_count = self.request.retries + 1
        logger.warning(f"send_finding_async failed, attempt {failed_count}: {str(exc)}")
        TASK_FAILURE.labels(task=task_name).inc()
        TASK_RETRY.labels(task=task_name).inc()
        
        # Check if this is the final retry
        if failed_count >= self.max_retries:
            backup_logger.error(f"send_finding_async failed after all retries: {str(exc)}")
            alert_service.send_task_failure_alert(
                task_name=task_name,
                error=f"Failed after {failed_count} attempts: {str(exc)}",
                context={
                    'finding_id': finding.get('id') if finding else None,
                    'retry_count': failed_count,
                    'last_error': str(exc)
                }
            )
        
        try:
            raise self.retry(exc=exc, countdown=min(60, 2 ** self.request.retries))
        except Retry:
            # Celery raises Retry to signal a retry attempt; re-raise
            raise


@celery_app.task(bind=True)
def archive_audit_logs(self, days: int = 30):
    """Archive audit logs older than `days` into `audit_logs_archive` table.

    This is a best-effort task: it will attempt to copy rows to archive table
    and delete originals. If the archive table does not exist, the task will
    log and skip.
    """
    try:
        from backend.database.supabase_client import direct_db_query
        import logging

        logger = logging.getLogger('qc.workers.archive')
        # Fetch old rows
        filters = f"created_at=lt.now()-interval'{days} days'"
        old = direct_db_query('audit_logs', method='GET', filters=filters)
        if not old:
            logger.info('archive_audit_logs: no rows older than %s days', days)
            return {'archived': 0}

        # Insert into archive table
        try:
            res = direct_db_query('audit_logs_archive', method='POST', payload=old)
            archived_count = len(res) if res else 0
        except Exception as e:
            logger.warning('archive table insert failed: %s', e)
            # Try creating archive table fallback: skip
            archived_count = 0

        # Delete originals if archived
        if archived_count:
            # build delete filters by ids
            ids = ','.join([str(row.get('id')) for row in old if row.get('id')])
            if ids:
                direct_db_query('audit_logs', method='DELETE', filters=f'id=in.({ids})')
        return {'archived': archived_count}
    except Exception as e:
        import logging
        logger = logging.getLogger('qc.workers.archive')
        logger.exception('archive_audit_logs exception: %s', e)
        raise


@celery_app.task(bind=True)
def create_monthly_partition(self):
    """Create a partition for next month if it does not exist.

    Partition name format: audit_logs_y{year}m{month:02d}
    """
    import datetime
    from backend.service.db_utils import create_partition_for_range
    now = datetime.datetime.utcnow()
    # compute first day of next month
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    start_date = datetime.date(year, month, 1)
    # compute first day of following month
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    partition_name = f"audit_logs_y{start_date.year}m{start_date.month:02d}"
    created = create_partition_for_range(start_date.isoformat(), end_date.isoformat(), partition_name)
    return {"partition": partition_name, "created": created}

@celery_app.task(name='backend.workers.tasks.verify_backups')
def verify_backups():
    """Run basic verification on latest DB dump and WAL tarball using scripts/verify_backup.sh

    This is a lightweight integrity check: `pg_restore -l` and `tar -tzf`.
    """
    import subprocess
    from backend.notifications.alert_service import alert_service
    
    script = os.path.join(os.getcwd(), 'scripts', 'verify_backup.sh')
    try:
        subprocess.check_call([script])
        return {'status': 'ok'}
    except subprocess.CalledProcessError as e:
        # Send alert on backup verification failure
        alert_service.send_backup_failure_alert(
            backup_type="verification",
            error=f"Backup verification script failed with exit code {e.returncode}",
            context={'exit_code': e.returncode, 'script': script}
        )
        raise


@celery_app.task(name='backend.workers.tasks.wal_g_base_backup')
def wal_g_base_backup():
    """Trigger wal-g base backup helper inside the Postgres container.

    This invokes `scripts/wal_g_backup.sh` which runs `wal-g backup-push`.
    The task will raise on non-zero exit to mark failure.
    """
    import subprocess
    from backend.notifications.alert_service import alert_service
    
    script = os.path.join(os.getcwd(), 'scripts', 'wal_g_backup.sh')
    if not os.path.exists(script):
        error_msg = f"wal-g backup script not found: {script}"
        alert_service.send_backup_failure_alert(
            backup_type="wal-g-base",
            error=error_msg
        )
        raise FileNotFoundError(error_msg)
    
    try:
        subprocess.check_call([script])
        return {'status': 'ok'}
    except subprocess.CalledProcessError as e:
        # Send alert on backup failure
        alert_service.send_backup_failure_alert(
            backup_type="wal-g-base",
            error=f"wal-g base backup failed with exit code {e.returncode}",
            context={'exit_code': e.returncode}
        )
        raise


@celery_app.task(bind=True, name='backend.workers.tasks.full_restore_smoke_test')
def full_restore_smoke_test(self):
    """Fetch latest wal-g backup and perform a lightweight smoke verification.

    This task fetches the latest backup into a temporary directory using
    `scripts/wal_g_restore.sh` and verifies that files were fetched.
    It does not attempt to start Postgres in this environment; the GitHub
    Actions workflow performs a full-restore verification there.
    """
    import subprocess
    import tempfile
    import shutil
    from backend.notifications.alert_service import alert_service

    script = os.path.join(os.getcwd(), 'scripts', 'wal_g_restore.sh')
    if not os.path.exists(script):
        error_msg = f"wal-g restore script not found: {script}"
        alert_service.send_backup_failure_alert('full-restore-smoke', error_msg)
        raise FileNotFoundError(error_msg)

    tmpdir = tempfile.mkdtemp(prefix='qc_restore_')
    try:
        subprocess.check_call([script, tmpdir])
        # Verify the restore directory contains files
        has_files = any(os.scandir(tmpdir))
        if not has_files:
            raise RuntimeError('Restore fetched no files')
        return {'status': 'ok', 'restored_to': tmpdir}
    except Exception as e:
        alert_service.send_backup_failure_alert('full-restore-smoke', str(e))
        raise
    finally:
        # Keep artifacts for debugging; caller/CI can clean up if desired
        pass
