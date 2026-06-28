"""Product analytics: persist key funnel/commerce events for ops dashboards."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.commerce import User

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductAnalyticsService:
    ALLOWED_EVENTS = frozenset(
        {
            "predict_submit",
            "predict_follow_ai",
            "ai_analysis_start",
            "ai_analysis_complete",
            "mint_order_create",
            "mint_order_paid",
            "chain_mint_success",
            "chain_mint_failed",
            "collectible_share",
            "page_view",
            "duel_match_enter",
            "duel_complete",
            "duel_season_tier_up",
            "duel_fee_sink",
        }
    )

    def __init__(self, db: Session):
        self.db = db

    def track(
        self,
        event_name: str,
        *,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if event_name not in self.ALLOWED_EVENTS:
            return {"ok": False, "reason": "event_not_allowed"}
        from app.db.models.commerce import ProductAnalyticsEvent

        row = ProductAnalyticsEvent(
            user_id=user_id,
            event_name=event_name,
            payload=payload or {},
            session_id=session_id,
        )
        self.db.add(row)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return {"ok": True}

    def summary(self, *, hours: int = 24) -> dict[str, Any]:
        from datetime import timedelta

        from sqlalchemy import func

        from app.db.models.commerce import ProductAnalyticsEvent

        since = _utcnow() - timedelta(hours=hours)
        rows = (
            self.db.query(ProductAnalyticsEvent.event_name, func.count())
            .filter(ProductAnalyticsEvent.created_at >= since)
            .group_by(ProductAnalyticsEvent.event_name)
            .all()
        )
        return {
            "window_hours": hours,
            "events": {name: int(cnt) for name, cnt in rows},
            "total": sum(int(c) for _, c in rows),
        }
