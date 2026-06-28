"""Admin 四合一监控：订单/打新/链/AI 队列快照。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ai_concurrency import llm_queue_depth
from app.core.config import get_settings
from app.db.models.commerce import AgentRun, Order, UserCollectibleCard


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AdminOpsDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def snapshot(self, *, window_hours: int = 24) -> dict[str, Any]:
        since = _utcnow() - timedelta(hours=window_hours)
        paid = (
            self.db.query(func.count(Order.id))
            .filter(Order.status == "paid", Order.paid_at >= since)
            .scalar()
            or 0
        )
        pending = (
            self.db.query(func.count(Order.id)).filter(Order.status == "pending").scalar() or 0
        )
        refunded = (
            self.db.query(func.count(Order.id))
            .filter(Order.status == "refunded", Order.updated_at >= since)
            .scalar()
            or 0
        )
        mint_orders = (
            self.db.query(func.count(Order.id))
            .filter(Order.mint_event_id.isnot(None), Order.status == "paid", Order.paid_at >= since)
            .scalar()
            or 0
        )
        chain_pending = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(UserCollectibleCard.chain_status.in_(("pending", "minting", "submitted")))
            .scalar()
            or 0
        )
        chain_failed = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(UserCollectibleCard.chain_status == "failed")
            .scalar()
            or 0
        )
        chain_failed_recent = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(
                UserCollectibleCard.chain_status == "failed",
                UserCollectibleCard.updated_at >= since,
            )
            .scalar()
            or 0
        )
        chain_none = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(
                (UserCollectibleCard.chain_status.is_(None))
                | (UserCollectibleCard.chain_status == "none")
            )
            .scalar()
            or 0
        )
        chain_error_rows = (
            self.db.query(UserCollectibleCard.chain_error, func.count())
            .filter(UserCollectibleCard.chain_status == "failed")
            .group_by(UserCollectibleCard.chain_error)
            .order_by(func.count().desc())
            .limit(5)
            .all()
        )
        chain_alert = chain_failed >= 5 or chain_failed_recent >= 3
        ai_runs = (
            self.db.query(func.count(AgentRun.id)).filter(AgentRun.created_at >= since).scalar() or 0
        )
        depth = llm_queue_depth()
        ai_active = int(depth.get("active") or 0)
        ai_limit = max(1, int(depth.get("limit") or 1))
        ai_util_pct = round(ai_active / ai_limit * 100, 1)
        ai_alert = ai_util_pct >= float(self.settings.ai_queue_alert_pct)
        from app.services.product_analytics_service import ProductAnalyticsService

        funnel = ProductAnalyticsService(self.db).summary(window_hours=window_hours)
        return {
            "window_hours": window_hours,
            "orders": {
                "paid": paid,
                "pending": pending,
                "refunded": refunded,
                "mint_paid": mint_orders,
                "success_rate_pct": round(paid / max(paid + refunded, 1) * 100, 1),
            },
            "chain": {
                "pending_mints": chain_pending,
                "failed_mints": chain_failed,
                "failed_recent": chain_failed_recent,
                "none_legacy": chain_none,
                "top_errors": [
                    {"error": (err or "")[:120], "count": int(cnt)} for err, cnt in chain_error_rows
                ],
                "alert": chain_alert,
                "avata_active": self.settings.avata_active,
            },
            "ai": {
                "runs": ai_runs,
                "queue": depth,
                "util_pct": ai_util_pct,
                "alert": ai_alert,
            },
            "redis_configured": bool((self.settings.redis_url or "").strip()),
            "funnel_events": funnel.get("events", {}),
            "funnel_total": funnel.get("total", 0),
            "production_mode": self.settings.production_mode,
            "alipay_mock": self.settings.alipay_mock,
            "avata_mock": self.settings.avata_mock,
        }
