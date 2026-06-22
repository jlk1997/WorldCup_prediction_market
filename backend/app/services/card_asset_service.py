"""足球数字资产平台 — 共享核心：序列号、冷却期、所有权转移、估值、成就。

所有二级流通（转赠/交易/打新）共用此处的所有权迁移与合规校验。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.data.asset_catalog import ACHIEVEMENTS, ACHIEVEMENT_BY_CODE, estimate_card_value
from app.db.models.commerce import (
    CardSerialCounter,
    CardTransferLog,
    CollectibleCard,
    MarketPricePoint,
    User,
    UserAchievement,
    UserCollectibleCard,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CardAssetService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    # ----------------------- 序列号 -----------------------
    def assign_serial(self, card_id: int) -> tuple[int, int | None]:
        """领取下一个序列号，返回 (serial_no, mint_total)。mint_total 仅限量卡有值。"""
        counter = (
            self.db.query(CardSerialCounter)
            .filter(CardSerialCounter.card_id == card_id)
            .with_for_update()
            .first()
        )
        if not counter:
            counter = CardSerialCounter(card_id=card_id, issued=0)
            self.db.add(counter)
            self.db.flush()
        counter.issued = (counter.issued or 0) + 1
        card = self.db.get(CollectibleCard, card_id)
        mint_total = None
        if card and card.attributes_json and isinstance(card.attributes_json, dict):
            mint_total = card.attributes_json.get("mint_total")
        return counter.issued, mint_total

    def backfill_serial(self, row: UserCollectibleCard) -> None:
        """为历史卡牌补发序列号与估值（懒加载时调用）。"""
        if row.serial_no:
            return
        serial, mint_total = self.assign_serial(row.card_id)
        row.serial_no = serial
        if mint_total:
            row.mint_total = mint_total
        card = self.db.get(CollectibleCard, row.card_id)
        if card and not row.acquired_value:
            row.acquired_value = estimate_card_value(
                card.rarity, row.star, serial_no=serial, mint_total=mint_total
            )

    # ----------------------- 冷却 / 锁定 -----------------------
    def apply_cooldown(self, row: UserCollectibleCard, *, days: int | None = None) -> None:
        d = self.settings.asset_holding_cooldown_days if days is None else days
        row.holding_until = _utcnow() + timedelta(days=d)

    def assert_real_name(self, user: User) -> None:
        if not user.real_name_verified:
            raise BadRequestError("请先完成实名认证后再进行流通操作")

    def assert_tradable(self, row: UserCollectibleCard) -> None:
        self.reconcile_stale_listing(row)
        if not row.tradable:
            raise BadRequestError("该卡牌不可流通")
        if (row.count or 1) > 1:
            raise BadRequestError("叠卡暂不可单独流通，请先在收藏册拆分叠卡")
        if row.lock_state and row.lock_state != "none":
            label = {"listed": "已在交易行挂牌", "staked": "已质押", "duel": "对决锁定中"}.get(
                row.lock_state, "锁定中"
            )
            raise BadRequestError(f"该卡牌{label}，请先取消后再操作")
        if row.holding_until and row.holding_until > _utcnow():
            left = row.holding_until - _utcnow()
            hours = int(left.total_seconds() // 3600) + 1
            raise BadRequestError(f"新获卡牌冷却中，约 {hours} 小时后可流通")
        self.assert_no_active_listing(row.id)
        self.assert_no_active_stake(row.id)

    def assert_no_active_listing(self, user_card_id: int) -> None:
        from app.db.models.commerce import CardListing

        now = _utcnow()
        exists = (
            self.db.query(CardListing.id)
            .filter(
                CardListing.user_card_id == user_card_id,
                CardListing.status == "active",
                or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
            )
            .first()
        )
        if exists:
            raise BadRequestError("该卡牌已在交易行挂牌中")

    def reconcile_stale_listing(self, row: UserCollectibleCard) -> None:
        """过期挂牌仍占 lock_state 时自动解锁（scheduler 未跑时的兜底）。"""
        from app.db.models.commerce import CardListing

        now = _utcnow()
        stale = (
            self.db.query(CardListing)
            .filter(
                CardListing.user_card_id == row.id,
                CardListing.status == "active",
                CardListing.expires_at.isnot(None),
                CardListing.expires_at <= now,
            )
            .with_for_update()
            .all()
        )
        if not stale:
            if row.lock_state == "listed":
                active = (
                    self.db.query(CardListing.id)
                    .filter(
                        CardListing.user_card_id == row.id,
                        CardListing.status == "active",
                        or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
                    )
                    .first()
                )
                if not active:
                    row.lock_state = "none"
            return
        for listing in stale:
            if listing.list_type == "auction" and listing.current_bidder_id and listing.current_bid:
                from app.services.marketplace_service import MarketplaceService

                MarketplaceService(self.db)._expire_auction(listing)
            else:
                listing.status = "expired"
                if row.lock_state == "listed":
                    row.lock_state = "none"
        self.db.flush()

    def assert_no_active_stake(self, user_card_id: int) -> None:
        from app.db.models.commerce import CardStake

        exists = (
            self.db.query(CardStake.id)
            .filter(CardStake.user_card_id == user_card_id, CardStake.status == "active")
            .first()
        )
        if exists:
            raise BadRequestError("该卡牌已质押中，请先赎回")

    # ----------------------- 所有权迁移 -----------------------
    def transfer_ownership(
        self,
        row: UserCollectibleCard,
        from_user: User,
        to_user: User,
        *,
        kind: str,
        points_amount: int = 0,
        fee_points: int = 0,
        apply_cooldown: bool = True,
        record_price: bool = False,
    ) -> dict[str, Any]:
        """把卡牌从 from_user 迁移到 to_user（DB + 链上）。

        合规：受让方不可已拥有同款卡（受唯一约束限制，保护序列号完整性）。
        """
        existing = (
            self.db.query(UserCollectibleCard)
            .filter(
                UserCollectibleCard.user_id == to_user.id,
                UserCollectibleCard.card_id == row.card_id,
            )
            .first()
        )
        if existing:
            raise BadRequestError("对方已拥有该卡，暂不支持受让重复卡")

        card = self.db.get(CollectibleCard, row.card_id)

        # 链上托管转移（best-effort）
        chain_status = "none"
        chain_tx = None
        chain_op = None
        try:
            from app.services.collectible_chain_service import CollectibleChainService

            chain = CollectibleChainService(self.db).transfer_card_onchain(from_user, to_user, row)
            chain_status = chain.get("status", "none")
            chain_tx = chain.get("tx_hash")
            chain_op = chain.get("operation_id")
        except Exception:
            logger.exception("chain transfer failed row=%s", row.id)

        # DB 迁移
        row.user_id = to_user.id
        row.source = kind
        row.lock_state = "none"
        row.updated_at = _utcnow()
        if apply_cooldown:
            self.apply_cooldown(row)
        if card and points_amount:
            row.acquired_value = points_amount

        log = CardTransferLog(
            card_id=row.card_id,
            user_card_id=row.id,
            from_user_id=from_user.id,
            to_user_id=to_user.id,
            kind=kind,
            points_amount=points_amount,
            fee_points=fee_points,
            chain_status=chain_status,
            chain_operation_id=chain_op,
            chain_tx_hash=chain_tx,
        )
        self.db.add(log)

        if record_price and points_amount > 0:
            self.db.add(
                MarketPricePoint(
                    card_id=row.card_id,
                    price_points=points_amount,
                    qty=1,
                    kind="trade" if kind == "trade" else kind,
                )
            )
        self.db.flush()
        return {
            "chain_status": chain_status,
            "chain_tx_hash": chain_tx,
            "transfer_log_id": log.id,
        }

    # ----------------------- 估值 / 组合 -----------------------
    def card_value(self, row: UserCollectibleCard, card: CollectibleCard) -> int:
        return estimate_card_value(
            card.rarity, row.star, serial_no=row.serial_no, mint_total=row.mint_total
        )

    def portfolio_value(self, user_id: int) -> int:
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user_id)
            .all()
        )
        return sum(self.card_value(r, c) for r, c in rows)

    # ----------------------- 成就 -----------------------
    def unlock_achievement(self, user_id: int, code: str) -> bool:
        if code not in ACHIEVEMENT_BY_CODE:
            return False
        exists = (
            self.db.query(UserAchievement.id)
            .filter(UserAchievement.user_id == user_id, UserAchievement.code == code)
            .first()
        )
        if exists:
            return False
        self.db.add(UserAchievement(user_id=user_id, code=code))
        self.db.flush()
        return True

    def evaluate_achievements(self, user: User) -> list[str]:
        """检测并解锁达成的成就，返回新解锁的 code 列表。"""
        owned = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(UserCollectibleCard.user_id == user.id)
            .scalar()
            or 0
        )
        legend_owned = (
            self.db.query(func.count(UserCollectibleCard.id))
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user.id, CollectibleCard.rarity == "legend")
            .scalar()
            or 0
        )
        trades = (
            self.db.query(func.count(CardTransferLog.id))
            .filter(CardTransferLog.to_user_id == user.id, CardTransferLog.kind == "trade")
            .scalar()
            or 0
        )
        from app.db.models.commerce import CardStake, FantasyLineup, MintReservation

        stakes = (
            self.db.query(func.count(CardStake.id)).filter(CardStake.user_id == user.id).scalar() or 0
        )
        fantasy = (
            self.db.query(func.count(FantasyLineup.id)).filter(FantasyLineup.user_id == user.id).scalar()
            or 0
        )
        mints = (
            self.db.query(func.count(MintReservation.id))
            .filter(MintReservation.user_id == user.id, MintReservation.claimed_count > 0)
            .scalar()
            or 0
        )
        from app.data.collab_catalog import COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL

        collab_owned = (
            self.db.query(func.count(UserCollectibleCard.id))
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.series.in_([COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL]),
            )
            .scalar()
            or 0
        )
        crest_teams = (
            self.db.query(func.count(func.distinct(CollectibleCard.team_id)))
            .join(UserCollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.series == "team_crest",
                CollectibleCard.team_id.isnot(None),
            )
            .scalar()
            or 0
        )
        portfolio = self.portfolio_value(user.id)

        metrics = {
            "owned": owned,
            "legend_owned": legend_owned,
            "trades": trades,
            "stakes": stakes,
            "fantasy": fantasy,
            "mints": mints,
            "collab_owned": collab_owned,
            "crest_teams": crest_teams,
            "portfolio": portfolio,
        }
        newly: list[str] = []
        for ach in ACHIEVEMENTS:
            if metrics.get(ach["metric"], 0) >= ach["threshold"]:
                if self.unlock_achievement(user.id, ach["code"]):
                    newly.append(ach["code"])
        return newly

    def list_achievements(self, user: User) -> list[dict[str, Any]]:
        unlocked = {
            r.code: r.unlocked_at
            for r in self.db.query(UserAchievement).filter(UserAchievement.user_id == user.id).all()
        }
        out = []
        for ach in ACHIEVEMENTS:
            out.append(
                {
                    "code": ach["code"],
                    "name": ach["name"],
                    "desc": ach["desc"],
                    "unlocked": ach["code"] in unlocked,
                    "unlocked_at": unlocked[ach["code"]].isoformat()
                    if unlocked.get(ach["code"])
                    else None,
                }
            )
        return out

    def owned_row(self, user: User, user_card_id: int, *, for_update: bool = False) -> UserCollectibleCard:
        q = self.db.query(UserCollectibleCard).filter(
            UserCollectibleCard.id == user_card_id,
            UserCollectibleCard.user_id == user.id,
        )
        if for_update:
            q = q.with_for_update()
        row = q.first()
        if not row:
            raise NotFoundError("卡牌不存在或不属于你")
        return row

    def split_stack(self, user: User, user_card_id: int, *, amount: int = 1) -> dict[str, Any]:
        """从叠卡堆中拆出独立卡牌（各赋新序列号，可单独流通）。"""
        if amount < 1:
            raise BadRequestError("拆分数量不合法")
        row = self.owned_row(user, user_card_id, for_update=True)
        stack = row.count or 1
        if stack <= 1:
            raise BadRequestError("该卡未叠卡，无需拆分")
        if amount >= stack:
            raise BadRequestError(f"至少保留 1 张在堆中，最多可拆分 {stack - 1} 张")
        if row.lock_state and row.lock_state != "none":
            label = {"listed": "挂牌中", "staked": "质押中", "duel": "对决中"}.get(row.lock_state, "锁定中")
            raise BadRequestError(f"卡牌{label}，请先解除后再拆分")
        self.reconcile_stale_listing(row)
        self.assert_no_active_stake(row.id)

        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")

        from app.data.asset_catalog import estimate_card_value

        new_ids: list[int] = []
        for _ in range(amount):
            serial, mint_total = self.assign_serial(row.card_id)
            new_row = UserCollectibleCard(
                user_id=user.id,
                card_id=row.card_id,
                star=row.star,
                count=1,
                source="split",
                highlight_json=row.highlight_json or [],
                tradable=bool(row.tradable),
                serial_no=serial,
                mint_total=mint_total,
                acquired_value=estimate_card_value(
                    card.rarity, row.star, serial_no=serial, mint_total=mint_total
                ),
                lock_state="none",
            )
            self.apply_cooldown(new_row)
            self.db.add(new_row)
            self.db.flush()
            new_ids.append(new_row.id)
            try:
                from app.services.collectible_chain_service import CollectibleChainService

                CollectibleChainService(self.db).queue_mint(user, new_row, card)
            except Exception:
                logger.exception("split chain queue failed row=%s", new_row.id)

        row.count = stack - amount
        row.updated_at = _utcnow()
        self.db.flush()
        return {
            "ok": True,
            "split_count": amount,
            "remaining_stack": row.count,
            "new_user_card_ids": new_ids,
            "notice": f"已拆分 {amount} 张，新卡进入 7 天冷却后可流通",
        }
