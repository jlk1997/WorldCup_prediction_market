"""API request quota tracking."""

from __future__ import annotations

from datetime import date

from app.core.cache import cache_get, cache_set

DAILY_LIMIT = 100
BSD_TRACKING_LIMIT = None  # informational only; BSD free tier has no hard daily cap


def _key(provider: str = "apifootball") -> str:
    return f"{provider}:quota:{date.today().isoformat()}"


def get_usage(provider: str = "bsd") -> dict:
    if provider == "bsd":
        used = int(cache_get(_key("bsd")) or 0)
        return {
            "provider": "bsd",
            "date": date.today().isoformat(),
            "used": used,
            "limit": None,
            "remaining": None,
            "note": "BSD free tier has no daily quota; count is for monitoring only",
        }
    used = int(cache_get(_key("apifootball")) or 0)
    return {
        "provider": "apifootball",
        "date": date.today().isoformat(),
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used),
    }


def can_request() -> bool:
    remaining = get_usage("apifootball").get("remaining")
    return bool(remaining and remaining > 0)


def record_request(count: int = 1) -> None:
    from app.core.cache import cache_incr

    cache_incr(_key("apifootball"), count)


def record_bsd_request(count: int = 1) -> None:
    from app.core.cache import cache_incr

    cache_incr(_key("bsd"), count)


def invalidate_live_cache() -> None:
    from app.core.cache import cache_delete

    cache_delete("live:matches")
    cache_delete("live:matches:full")
    cache_delete("live:grouped")
