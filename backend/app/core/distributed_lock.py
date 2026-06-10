"""Distributed lock via Redis SET NX, with in-process fallback."""

from __future__ import annotations

import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)

_local_locks: dict[str, tuple[str, float]] = {}
_local_guard = threading.Lock()


def _redis_client():
    from app.core.redis_client import get_redis_client

    return get_redis_client()


def try_acquire_lock(key: str, ttl_sec: int = 300) -> str | None:
    """Return lock token if acquired, else None."""
    token = uuid.uuid4().hex
    r = _redis_client()
    if r is not None:
        try:
            if r.set(key, token, nx=True, ex=max(1, ttl_sec)):
                return token
            return None
        except Exception as exc:
            logger.debug("Redis lock failed, fallback local: %s", exc)

    now = time.time()
    with _local_guard:
        existing = _local_locks.get(key)
        if existing and existing[1] > now:
            return None
        _local_locks[key] = (token, now + ttl_sec)
        return token


def release_lock(key: str, token: str) -> None:
    r = _redis_client()
    if r is not None:
        try:
            script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """
            r.eval(script, 1, key, token)
            return
        except Exception as exc:
            logger.debug("Redis unlock failed: %s", exc)

    with _local_guard:
        existing = _local_locks.get(key)
        if existing and existing[0] == token:
            del _local_locks[key]


class distributed_lock:
    def __init__(self, key: str, ttl_sec: int = 300):
        self.key = key
        self.ttl_sec = ttl_sec
        self.token: str | None = None

    def __enter__(self) -> bool:
        self.token = try_acquire_lock(self.key, self.ttl_sec)
        return self.token is not None

    def __exit__(self, *args) -> None:
        if self.token:
            release_lock(self.key, self.token)
