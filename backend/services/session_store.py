"""Small expiring key-value store used for auth session state.

The production target for this project is Vercel + Supabase, so the app does
not depend on external cache. This module keeps the previous `get_session_store()` call surface
for auth code and tests while using an in-process store.
"""

from __future__ import annotations

import time
from collections import defaultdict


class MemoryStore:
    def __init__(self):
        self._values: dict[str, tuple[str, float | None]] = {}
        self._sets: dict[str, set[str]] = defaultdict(set)

    def _expired(self, key: str) -> bool:
        item = self._values.get(key)
        if not item:
            return True
        _, expires_at = item
        if expires_at and expires_at < time.time():
            self._values.pop(key, None)
            return True
        return False

    def set(self, key: str, value: str, ex: int | None = None):
        expires_at = time.time() + ex if ex else None
        self._values[key] = (value, expires_at)
        return True

    def get(self, key: str):
        if self._expired(key):
            return None
        return self._values[key][0]

    def delete(self, key: str):
        existed = key in self._values
        self._values.pop(key, None)
        self._sets.pop(key, None)
        return int(existed)

    def incr(self, key: str):
        value = int(self.get(key) or 0) + 1
        self.set(key, str(value))
        return value

    def expire(self, key: str, seconds: int):
        if key in self._values:
            value, _ = self._values[key]
            self._values[key] = (value, time.time() + seconds)
        return True

    def sadd(self, key: str, value: str):
        self._sets[key].add(value)
        return 1

    def sismember(self, key: str, value: str):
        return value in self._sets.get(key, set())


_CLIENT = MemoryStore()


def get_session_store() -> MemoryStore:
    return _CLIENT
