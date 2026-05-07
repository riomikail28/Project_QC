"""Database utilities for administrative operations (DDL) using psycopg2.

Provides helpers to create partitions and run maintenance SQL that cannot
be performed via Supabase REST API.
"""
import os
import logging
from contextlib import contextmanager
import psycopg2
import psycopg2.extras

logger = logging.getLogger('qc.db.utils')


def get_conn():
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise RuntimeError('DATABASE_URL is not configured')
    return psycopg2.connect(dsn)


@contextmanager
def db_cursor(commit: bool = True):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def create_partition_for_range(start_date: str, end_date: str, partition_name: str) -> bool:
    """Create a partition table for audit_logs between start_date and end_date.

    Dates should be in ISO format e.g. '2026-06-01'
    Returns True if created or already exists.
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF audit_logs
    FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """
    try:
        with db_cursor() as cur:
            cur.execute(sql)
        logger.info('Created partition %s for %s - %s', partition_name, start_date, end_date)
        return True
    except Exception as e:
        logger.exception('Failed to create partition %s: %s', partition_name, e)
        return False
