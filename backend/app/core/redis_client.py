"""Shared Redis client singleton with connection pool."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_client_url: str | None = None


def get_redis_client():
    from app.core.config import get_settings

    global _client, _client_url
    settings = get_settings()
    url = (settings.redis_url or "").strip()
    if not url:
        return None
    if _client is not None and _client_url == url:
        return _client
    try:
        import redis

        _client = redis.from_url(url, max_connections=20, decode_responses=False)
        _client_url = url
        return _client
    except Exception as exc:
        logger.debug("Redis client init failed: %s", exc)
        return None


def reset_redis_client_for_tests() -> None:
    global _client, _client_url
    _client = None
    _client_url = None
