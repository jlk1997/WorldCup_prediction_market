"""经济健康看板：积分通胀/sink、交易行成交、回购支出、质押产出（运营调参用）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.commerce import (
    CardListing,
    CardStake,
    CardTransferLog,
    MarketPricePoint,
    PointLedger,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EconomyService:
    def __init__(self, db: Session):
        self.db = db

    def dashboard(self, days: int = 7) -> dict[str, Any]:
        since = _utcnow() - timedelta(days=days)

        # 可用积分 faucet / sink（按 reason 汇总）
        rows = (
            self.db.query(
                PointLedger.reason,
                func.sum(PointLedger.delta).label("net"),
                func.count(PointLedger.id).label("cnt"),
            )
            .filter(PointLedger.point_bucket == "redeem", PointLedger.created_at >= since)
            .group_by(PointLedger.reason)
            .all()
        )
        faucet = {}
        sink = {}
        total_in = total_out = 0
        for reason, net, cnt in rows:
            net = int(net or 0)
            if net >= 0:
                faucet[reason] = {"amount": net, "count": int(cnt)}
                total_in += net
            else:
                sink[reason] = {"amount": -net, "count": int(cnt)}
                total_out += -net

        # 交易行成交
        trade_vol = (
            self.db.query(func.coalesce(func.sum(MarketPricePoint.price_points), 0))
            .filter(MarketPricePoint.kind == "trade", MarketPricePoint.created_at >= since)
            .scalar()
            or 0
        )
        trade_cnt = (
            self.db.query(func.count(MarketPricePoint.id))
            .filter(MarketPricePoint.kind == "trade", MarketPricePoint.created_at >= since)
            .scalar()
            or 0
        )
        fee_sink = (
            self.db.query(func.coalesce(func.sum(CardTransferLog.fee_points), 0))
            .filter(CardTransferLog.kind == "trade", CardTransferLog.created_at >= since)
            .scalar()
            or 0
        )
        buyback_spend = (
            self.db.query(func.coalesce(func.sum(CardTransferLog.points_amount), 0))
            .filter(CardTransferLog.kind == "buyback", CardTransferLog.created_at >= since)
            .scalar()
            or 0
        )
        gift_cnt = (
            self.db.query(func.count(CardTransferLog.id))
            .filter(CardTransferLog.kind == "gift", CardTransferLog.created_at >= since)
            .scalar()
            or 0
        )
        active_listings = (
            self.db.query(func.count(CardListing.id))
            .filter(CardListing.status == "active")
            .scalar()
            or 0
        )
        active_stakes = (
            self.db.query(func.count(CardStake.id))
            .filter(CardStake.status == "active")
            .scalar()
            or 0
        )
        stake_yield = (
            self.db.query(func.coalesce(func.sum(CardStake.total_claimed), 0)).scalar() or 0
        )

        net_flow = total_in - total_out
        inflation_pct = round((net_flow / total_in * 100), 2) if total_in else 0.0

        return {
            "window_days": days,
            "redeem_points": {
                "total_in": total_in,
                "total_out": total_out,
                "net_flow": net_flow,
                "inflation_pct": inflation_pct,
                "faucet": faucet,
                "sink": sink,
            },
            "marketplace": {
                "trade_volume": int(trade_vol),
                "trade_count": int(trade_cnt),
                "fee_sink": int(fee_sink),
                "active_listings": int(active_listings),
            },
            "buyback_spend": int(buyback_spend),
            "gift_count": int(gift_cnt),
            "staking": {
                "active_stakes": int(active_stakes),
                "total_yield_claimed": int(stake_yield),
            },
            "health_hint": self._health_hint(inflation_pct),
        }

    @staticmethod
    def _health_hint(inflation_pct: float) -> str:
        if inflation_pct > 40:
            return "通胀偏高：建议提高手续费/回购门槛或增加 sink（合成/打新）"
        if inflation_pct < -10:
            return "通缩偏紧：建议提高竞猜积分产出或降低手续费"
        return "经济健康区间"
