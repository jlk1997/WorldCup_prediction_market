"""Platform-wide daily AI token budget with atomic reserve/release."""

from __future__ import annotations

import logging
import threading
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.db.models.commerce import AiUsageDaily

logger = logging.getLogger(__name__)

ESTIMATED_TOKENS_PER_ANALYZE = 50_000

_fallback_lock = threading.RLock()
_fallback_reserved: dict[str, int] = {}


def _today() -> date:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None).date()


def _redis_keys(d: date) -> tuple[str, str]:
    ds = d.isoformat()
    return f"ai:budget:consumed:{ds}", f"ai:budget:reserved:{ds}"


def _redis_incr(key: str, delta: int, ttl: int = 86400 * 2) -> int | None:
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis

        r = redis.from_url(settings.redis_url)
        pipe = r.pipeline()
        pipe.incrby(key, delta)
        pipe.expire(key, ttl)
        val, _ = pipe.execute()
        return int(val)
    except Exception as exc:
        logger.debug("Redis token budget fallback: %s", exc)
        return None


def _redis_get(key: str) -> int | None:
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis

        val = redis.from_url(settings.redis_url).get(key)
        return int(val) if val else 0
    except Exception:
        return None


class AiTokenBudgetService:
    def __init__(self, db: Session | None = None):
        self.db = db
        self.settings = get_settings()

    def _total_used(self, d: date | None = None) -> int:
        d = d or _today()
        consumed_k, reserved_k = _redis_keys(d)
        c = _redis_get(consumed_k)
        r = _redis_get(reserved_k)
        if c is not None and r is not None:
            return c + r

        db_total = 0
        if self.db:
            total = (
                self.db.query(func.coalesce(func.sum(AiUsageDaily.tokens_total), 0))
                .filter(AiUsageDaily.usage_date == d)
                .scalar()
            )
            db_total = int(total or 0)

        with _fallback_lock:
            local_reserved = _fallback_reserved.get(d.isoformat(), 0)
        return db_total + local_reserved

    def assert_can_reserve(self, estimate: int = ESTIMATED_TOKENS_PER_ANALYZE) -> None:
        if self._total_used() + estimate > self.settings.ai_daily_token_budget:
            raise ServiceUnavailableError("平台今日 AI 算力已达上限，请明日再试")

    def reserve(self, estimate: int = ESTIMATED_TOKENS_PER_ANALYZE) -> None:
        self.assert_can_reserve(estimate)
        _, reserved_k = _redis_keys(_today())
        new_val = _redis_incr(reserved_k, estimate)
        if new_val is not None:
            if new_val > self.settings.ai_daily_token_budget:
                _redis_incr(reserved_k, -estimate)
                raise ServiceUnavailableError("平台今日 AI 算力已达上限，请明日再试")
            return

        d_key = _today().isoformat()
        with _fallback_lock:
            self.assert_can_reserve(estimate)
            _fallback_reserved[d_key] = _fallback_reserved.get(d_key, 0) + estimate

    def release_reserved(self, estimate: int = ESTIMATED_TOKENS_PER_ANALYZE) -> None:
        _, reserved_k = _redis_keys(_today())
        if _redis_get(reserved_k) is not None:
            _redis_incr(reserved_k, -estimate)
            return
        d_key = _today().isoformat()
        with _fallback_lock:
            _fallback_reserved[d_key] = max(0, _fallback_reserved.get(d_key, 0) - estimate)

    def commit_consumed(self, actual_tokens: int, estimate: int = ESTIMATED_TOKENS_PER_ANALYZE) -> None:
        consumed_k, reserved_k = _redis_keys(_today())
        if _redis_get(reserved_k) is not None:
            _redis_incr(reserved_k, -estimate)
            _redis_incr(consumed_k, max(0, actual_tokens))
            return
        # tokens recorded via AiUsageDaily.add_tokens in billing service
