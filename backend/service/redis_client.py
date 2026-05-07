"""Simple Redis client singleton wrapper."""
import os
from redis import Redis

_CLIENT = None


def get_redis() -> Redis:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _CLIENT = Redis.from_url(redis_url, decode_responses=True)
    return _CLIENT
