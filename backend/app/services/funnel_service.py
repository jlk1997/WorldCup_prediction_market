"""Cold-start funnel metrics for weekly ops review."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.commerce import GamePrediction, Order, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FunnelService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, days: int = 7) -> dict:
        days = max(1, min(days, 90))
        now = _utcnow()
        since = now - timedelta(days=days)
        d7_cutoff = now - timedelta(days=7)

        registered = (
            self.db.query(func.count(User.id))
            .filter(User.created_at >= since, User.status == "active")
            .scalar()
            or 0
        )
        profile_done = (
            self.db.query(func.count(User.id))
            .filter(
                User.created_at >= since,
                User.status == "active",
                User.profile_completed.is_(True),
            )
            .scalar()
            or 0
        )
        first_predict_subq = (
            self.db.query(GamePrediction.user_id)
            .join(User, GamePrediction.user_id == User.id)
            .filter(User.created_at >= since, User.status == "active")
            .group_by(GamePrediction.user_id)
            .having(func.min(GamePrediction.created_at) >= since)
            .subquery()
        )
        first_predict = (
            self.db.query(func.count())
            .select_from(first_predict_subq)
            .scalar()
            or 0
        )
        paid_users = (
            self.db.query(func.count(func.distinct(Order.user_id)))
            .join(User, Order.user_id == User.id)
            .filter(
                User.created_at >= since,
                User.status == "active",
                Order.status == "paid",
            )
            .scalar()
            or 0
        )
        d7_cohort = (
            self.db.query(func.count(User.id))
            .filter(
                User.created_at <= d7_cutoff,
                User.created_at >= since,
                User.status == "active",
            )
            .scalar()
            or 0
        )
        d7_active = (
            self.db.query(func.count(User.id))
            .filter(
                User.created_at <= d7_cutoff,
                User.created_at >= since,
                User.status == "active",
                User.last_signin_date.isnot(None),
                User.last_signin_date >= func.date(User.created_at) + 7,
            )
            .scalar()
            or 0
        )

        def pct(num: int, den: int) -> float | None:
            if not den:
                return None
            return round(num / den * 100, 1)

        return {
            "period_days": days,
            "since": since.isoformat(),
            "registered": registered,
            "profile_completed": profile_done,
            "first_predict_users": first_predict,
            "paid_users": paid_users,
            "rates": {
                "profile_rate_pct": pct(profile_done, registered),
                "first_predict_rate_pct": pct(first_predict, registered),
                "paid_rate_pct": pct(paid_users, registered),
                "d7_signin_proxy_pct": pct(d7_active, d7_cohort),
            },
            "d7_cohort_size": d7_cohort,
            "note": "d7_signin_proxy 以注册满 7 天后仍有签到记录估算，非精确 D7 留存",
        }
