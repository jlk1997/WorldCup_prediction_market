"""Short-TTL caches for per-user dashboard surfaces (today-home, daily-status)."""

from __future__ import annotations

from app.core.cache import cache_delete, cache_get, cache_set

TODAY_HOME_TTL = 15
DAILY_STATUS_TTL = 15
LIVE_MINTS_TTL = 30
SHOP_PRODUCTS_TTL = 120
MARKET_CARD_TTL = 45


def today_home_key(user_id: int) -> str:
    return f"today_home:{user_id}"


def daily_status_key(user_id: int) -> str:
    return f"daily_status:{user_id}"


def invalidate_user_surface(user_id: int) -> None:
    cache_delete(today_home_key(user_id))
    cache_delete(daily_status_key(user_id))


def get_daily_status_cached(user_id: int):
    return cache_get(daily_status_key(user_id))


def set_daily_status_cached(user_id: int, payload: dict) -> None:
    cache_set(daily_status_key(user_id), payload, ttl=DAILY_STATUS_TTL)
