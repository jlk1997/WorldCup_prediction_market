"""卡牌流通（低风险）：实名转赠 + 官方积分回购。计价一律为可用积分。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import (
    CardTransferLog,
    CollectibleCard,
    MarketPricePoint,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository
from app.services.card_asset_service import CardAssetService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CardTransferService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)
        self.asset = CardAssetService(db)

    # ----------------------- 转赠 -----------------------
    def _gift_count(self, user_id: int, since: datetime) -> int:
        return (
            self.db.query(func.count(CardTransferLog.id))
            .filter(
                CardTransferLog.from_user_id == user_id,
                CardTransferLog.kind == "gift",
                CardTransferLog.created_at >= since,
            )
            .scalar()
            or 0
        )

    def gift(self, user: User, user_card_id: int, to_invite_code: str) -> dict[str, Any]:
        self.asset.assert_real_name(user)
        user_locked = (
            self.db.query(User).filter(User.id == user.id).with_for_update().first()
        )
        if not user_locked:
            raise NotFoundError("用户不存在")
        to_code = (to_invite_code or "").strip().upper()
        if not to_code:
            raise BadRequestError("请输入对方邀请码")
        recipient = self.db.query(User).filter(func.upper(User.invite_code) == to_code).first()
        if not recipient:
            raise NotFoundError("未找到该邀请码对应的用户")
        if recipient.id == user.id:
            raise BadRequestError("不能赠送给自己")
        self.asset.assert_real_name(recipient)

        # 限频
        day_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        season_start = _utcnow() - timedelta(days=90)
        if self._gift_count(user_locked.id, day_start) >= self.settings.asset_gift_daily_limit:
            raise BadRequestError(f"今日转赠已达上限（{self.settings.asset_gift_daily_limit} 次）")
        if self._gift_count(user_locked.id, season_start) >= self.settings.asset_gift_season_limit:
            raise BadRequestError("本季转赠已达上限")

        row = self.asset.owned_row(user_locked, user_card_id, for_update=True)
        self.asset.assert_tradable(row)
        card = self.db.get(CollectibleCard, row.card_id)

        result = self.asset.transfer_ownership(
            row, user_locked, recipient, kind="gift", apply_cooldown=True
        )
        self.asset.evaluate_achievements(recipient)
        self.db.commit()
        return {
            "ok": True,
            "to_nickname": recipient.nickname,
            "card_name": card.name if card else None,
            "chain": {"status": result["chain_status"], "tx_hash": result["chain_tx_hash"]},
            "notice": "转赠成功（站内虚拟藏品，无现金价值）",
        }

    # ----------------------- 官方回购 -----------------------
    def buyback_quote(self, rarity: str, star: int = 1) -> int:
        floor = self.settings.asset_buyback_floor_map.get(rarity, 0)
        # 升星溢价
        mult = {1: 1.0, 2: 1.4, 3: 2.0}.get(int(star or 1), 1.0)
        return int(floor * mult)

    def buyback(self, user: User, user_card_id: int) -> dict[str, Any]:
        self.asset.assert_real_name(user)
        user_locked = (
            self.db.query(User).filter(User.id == user.id).with_for_update().first()
        )
        if not user_locked:
            raise NotFoundError("用户不存在")
        row = self.asset.owned_row(user_locked, user_card_id, for_update=True)
        self.asset.assert_tradable(row)
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")
        amount = self.buyback_quote(card.rarity, row.star)
        if amount <= 0:
            raise BadRequestError("该卡暂不支持官方回购")

        # 链上回购回收（best-effort：标记不再流通）
        chain_note = "none"
        if row.chain_nft_id and row.chain_status == "minted":
            try:
                from app.services.collectible_chain_service import CollectibleChainService

                CollectibleChainService(self.db).mark_recalled(row)
                chain_note = "recalled"
            except Exception:
                logger.exception("buyback chain recall failed row=%s", row.id)

        # 记录回购流水 + 行情点（积分计价）
        self.db.add(
            CardTransferLog(
                card_id=row.card_id,
                user_card_id=row.id,
                from_user_id=user.id,
                to_user_id=None,
                kind="buyback",
                points_amount=amount,
                note="official_buyback",
            )
        )
        self.db.add(
            MarketPricePoint(card_id=row.card_id, price_points=amount, qty=1, kind="buyback")
        )
        # 删除持有行（卡牌被平台回收）
        self.db.delete(row)
        self.wallet.add_redeem_points(user_locked, amount, "card_buyback", "card", card.id)
        self.db.commit()
        return {
            "ok": True,
            "points_gained": amount,
            "currency": "redeem_points",
            "chain": chain_note,
            "notice": "官方回购完成，已返还可用积分（无现金价值）",
        }

    # ----------------------- 流转历史 -----------------------
    def history(self, user: User, limit: int = 30) -> list[dict[str, Any]]:
        rows = (
            self.db.query(CardTransferLog, CollectibleCard)
            .join(CollectibleCard, CardTransferLog.card_id == CollectibleCard.id)
            .filter(
                (CardTransferLog.from_user_id == user.id)
                | (CardTransferLog.to_user_id == user.id)
            )
            .order_by(CardTransferLog.id.desc())
            .limit(min(limit, 100))
            .all()
        )
        out = []
        for log, card in rows:
            direction = "out" if log.from_user_id == user.id else "in"
            out.append(
                {
                    "id": log.id,
                    "kind": log.kind,
                    "direction": direction,
                    "card_name": card.name,
                    "rarity": card.rarity,
                    "points_amount": log.points_amount,
                    "fee_points": log.fee_points,
                    "at": log.created_at.isoformat() if log.created_at else None,
                }
            )
        return out
