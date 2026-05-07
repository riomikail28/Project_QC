"""Idempotency helper for Celery tasks using Redis.

Usage:
    @idempotent_task(lambda args, kwargs: f"key-{args[0]}", ttl=300)
    def task(...):
        ...

This will attempt to acquire a Redis key before running the task. If key
exists, the task is considered duplicate and will be no-op.
"""
from functools import wraps
from typing import Callable, Any
from backend.service.redis_client import get_redis


def idempotent_task(key_fn: Callable[[tuple, dict], str], ttl: int = 300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = get_redis()
            key = key_fn(args, kwargs)
            lock_key = f"task:idemp:{key}"
            # Try set nx
            acquired = False
            try:
                acquired = r.set(lock_key, "1", nx=True, ex=ttl)
            except Exception:
                # If Redis not available, fall through to run (best-effort)
                acquired = True

            if not acquired:
                # Duplicate: skip
                return None

            try:
                return func(*args, **kwargs)
            finally:
                # Optionally let TTL expire; do not delete to avoid race conditions
                pass

        return wrapper

    return decorator
