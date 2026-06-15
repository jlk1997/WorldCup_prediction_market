"""Invalidate cached match/schedule data after sync or settlement."""

from __future__ import annotations

import logging

from app.core.cache import cache_delete
from app.ingest.quota import invalidate_live_cache

logger = logging.getLogger(__name__)

_SCHEDULE_KEYS = (
    "schedule:all",
    "schedule:bracket",
    "schedule:standings:local",
    "stats:overview",
)


def invalidate_match_caches() -> None:
    """Clear live + schedule caches (safe to call from sync, link, settle)."""
    try:
        invalidate_live_cache()
    except Exception as exc:
        logger.debug("invalidate_live_cache failed: %s", exc)
    for key in _SCHEDULE_KEYS:
        try:
            cache_delete(key)
        except Exception as exc:
            logger.debug("cache_delete %s failed: %s", key, exc)
