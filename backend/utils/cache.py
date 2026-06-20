"""Lightweight hybrid cache supporting local memory and Vercel KV / Upstash Redis REST APIs."""

from __future__ import annotations

import json
import logging
import os
import time
from threading import RLock
from typing import Any, Hashable

logger = logging.getLogger("qc.cache")


class TTLCache:
    def __init__(self, max_items: int = 128):
        self.max_items = max_items
        self._items: dict[Hashable, tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: Hashable):
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: Hashable, value: Any, ttl_seconds: float):
        if ttl_seconds <= 0:
            return value
        expires_at = time.monotonic() + ttl_seconds
        with self._lock:
            if len(self._items) >= self.max_items:
                oldest_key = min(self._items, key=lambda item_key: self._items[item_key][0])
                self._items.pop(oldest_key, None)
            self._items[key] = (expires_at, value)
        return value

    def clear(self):
        with self._lock:
            self._items.clear()


class HybridCache:
    def __init__(self, prefix: str, max_items: int = 128):
        self.prefix = prefix
        self.local_cache = TTLCache(max_items=max_items)
        self.url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
        self.token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if self.url and self.url.endswith("/"):
            self.url = self.url[:-1]

    def _stringify_key(self, key: Hashable) -> str:
        try:
            return f"{self.prefix}:{json.dumps(key, sort_keys=True)}"
        except Exception:
            return f"{self.prefix}:{str(key)}"

    def _run_kv_command(self, command: list) -> Any:
        if not self.url or not self.token:
            return None
        import urllib.request

        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(command).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=0.8) as response:  # nosec B310
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("result")
        except Exception as e:
            logger.debug("KV REST command failed: %s", e)
            return None

    def get(self, key: Hashable) -> Any:
        # Try local memory first
        val = self.local_cache.get(key)
        if val is not None:
            return val

        # Fallback to Vercel KV / Upstash Redis REST
        if self.url and self.token:
            str_key = self._stringify_key(key)
            res = self._run_kv_command(["GET", str_key])
            if res is not None:
                try:
                    parsed = json.loads(res)
                    # Cache locally for 10 seconds to avoid REST calls
                    self.local_cache.set(key, parsed, ttl_seconds=10.0)
                    return parsed
                except Exception:
                    return None
        return None

    def set(self, key: Hashable, value: Any, ttl_seconds: float) -> Any:
        self.local_cache.set(key, value, ttl_seconds)
        if self.url and self.token:
            str_key = self._stringify_key(key)
            try:
                serialized = json.dumps(value)
                self._run_kv_command(["SETEX", str_key, int(max(ttl_seconds, 1)), serialized])
            except Exception:
                pass
        return value

    def clear(self):
        self.local_cache.clear()


dashboard_cache = HybridCache(prefix="dashboard", max_items=128)
monitoring_schedule_cache = HybridCache(prefix="monitoring", max_items=64)
