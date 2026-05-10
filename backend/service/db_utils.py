"""Database utilities for administrative operations (DDL) using psycopg (v3).

Provides helpers to create partitions and run maintenance SQL that cannot
be performed via Supabase REST API.

Migration: Upgraded from psycopg2-binary to psycopg v3 for better Python 3.12+
compatibility and native support on serverless platforms like Vercel.
"""
import os
import logging
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger('qc.db.utils')


def get_conn():
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise RuntimeError('DATABASE_URL is not configured')
    return psycopg.connect(dsn)


@contextmanager
def db_cursor(commit: bool = True):
    conn = get_conn()
    try:
        cur = conn.cursor(row_factory=dict_row)
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
