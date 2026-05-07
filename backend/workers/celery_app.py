"""Celery application factory for background tasks."""
import os
from celery import Celery
from celery.schedules import crontab


def make_celery(app_name=__name__):
    broker = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    backend = os.environ.get("CELERY_RESULT_BACKEND", broker)
    celery = Celery(app_name, broker=broker, backend=backend)
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    # Default beat schedule can be overridden via CELERY_BEAT_SCHEDULE env var (JSON)
    # Provide sensible defaults for periodic maintenance tasks
    celery.conf.beat_schedule = {
        'archive-audit-logs-daily': {
            'task': 'backend.workers.tasks.archive_audit_logs',
            'schedule': crontab(hour=2, minute=0),
            'args': (),
        },
        'create-monthly-partition': {
            'task': 'backend.workers.tasks.create_monthly_partition',
            'schedule': crontab(day_of_month='1', hour=3, minute=0),
            'args': (),
        },
        'verify-backups-daily': {
            'task': 'backend.workers.tasks.verify_backups',
            'schedule': crontab(hour=4, minute=30),
            'args': (),
        },
        'wal-g-base-backup-nightly': {
            'task': 'backend.workers.tasks.wal_g_base_backup',
            'schedule': crontab(hour=1, minute=30),
            'args': (),
        }
    }
    return celery


# Create module-level celery app
celery_app = make_celery()
