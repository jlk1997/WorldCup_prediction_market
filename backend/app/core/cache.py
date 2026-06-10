"""Simple in-memory cache with optional Redis fallback."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

_memory: dict[str, tuple[float, Any]] = {}


def cache_get(key: str) -> Any | None:
    r = get_redis_client()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception as exc:
            logger.debug("Redis get failed, fallback memory: %s", exc)

    item = _memory.get(key)
    if not item:
        return None
    expires, value = item
    if time.time() > expires:
        del _memory[key]
        return None
    return value


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    r = get_redis_client()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception as exc:
            logger.debug("Redis set failed, fallback memory: %s", exc)

    _memory[key] = (time.time() + ttl, value)


def cache_delete(key: str) -> None:
    r = get_redis_client()
    if r:
        try:
            r.delete(key)
            return
        except Exception as exc:
            logger.debug("Redis delete failed, fallback memory: %s", exc)

    _memory.pop(key, None)


def cache_incr(key: str, delta: int = 1, ttl: int = 86400) -> int:
    r = get_redis_client()
    if r:
        try:
            pipe = r.pipeline()
            pipe.incrby(key, delta)
            pipe.expire(key, ttl)
            val, _ = pipe.execute()
            return int(val)
        except Exception as exc:
            logger.debug("Redis incr failed, fallback memory: %s", exc)

    item = _memory.get(key)
    current = int(item[1]) if item and time.time() <= item[0] else 0
    new_val = current + delta
    _memory[key] = (time.time() + ttl, new_val)
    return new_val


def cache_delete_prefix(prefix: str) -> None:
    r = get_redis_client()
    if r:
        try:
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor=cursor, match=f"{prefix}*", count=100)
                if keys:
                    r.delete(*keys)
                if cursor == 0:
                    break
            return
        except Exception as exc:
            logger.debug("Redis prefix delete failed, fallback memory: %s", exc)

    for key in list(_memory.keys()):
        if key.startswith(prefix):
            del _memory[key]
