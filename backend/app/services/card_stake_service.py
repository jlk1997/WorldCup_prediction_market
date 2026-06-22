"""卡牌质押：锁定卡牌产被动可用积分 + 为相关球队竞猜加成。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import CardStake, CollectibleCard, User, UserCollectibleCard
from app.db.repositories.user_repository import WalletRepository
from app.services.card_asset_service import CardAssetService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CardStakeService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)
        self.asset = CardAssetService(db)

    def _daily_yield(self, rarity: str) -> int:
        return self.settings.asset_stake_daily_yield_map.get(rarity, 0)

    def _accrued(self, stake: CardStake) -> int:
        last = stake.last_claim_at or stake.staked_at
        if not last:
            return 0
        seconds = (_utcnow() - last).total_seconds()
        days = seconds / 86400.0
        card = self.db.get(CollectibleCard, stake.card_id)
        rarity = card.rarity if card else stake.rarity
        return int(self._daily_yield(rarity) * days)

    def stake(self, user: User, user_card_id: int) -> dict[str, Any]:
        row = self.asset.owned_row(user, user_card_id, for_update=True)
        self.asset.reconcile_stale_listing(row)
        if row.lock_state == "staked":
            raise BadRequestError("该卡已质押")
        if row.lock_state == "listed":
            raise BadRequestError("该卡正在交易行挂牌，请先下架")
        if (row.count or 1) > 1:
            raise BadRequestError("叠卡暂不可质押，请先在收藏册拆分叠卡")
        self.asset.assert_no_active_listing(row.id)
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")
        if self._daily_yield(card.rarity) <= 0:
            raise BadRequestError("该稀有度暂不支持质押")

        row.lock_state = "staked"
        stake = CardStake(
            user_id=user.id,
            user_card_id=row.id,
            card_id=row.card_id,
            rarity=card.rarity,
            status="active",
            staked_at=_utcnow(),
            last_claim_at=_utcnow(),
        )
        self.db.add(stake)
        self.db.flush()
        self.asset.evaluate_achievements(user)
        self.db.commit()
        return {"ok": True, "stake_id": stake.id, "daily_yield": self._daily_yield(card.rarity)}

    def claim(self, user: User, stake_id: int) -> dict[str, Any]:
        stake = (
            self.db.query(CardStake)
            .filter(CardStake.id == stake_id, CardStake.user_id == user.id, CardStake.status == "active")
            .with_for_update()
            .first()
        )
        if not stake:
            raise NotFoundError("质押记录不存在")
        amount = self._accrued(stake)
        if amount <= 0:
            raise BadRequestError("暂无可领取收益")
        stake.last_claim_at = _utcnow()
        stake.total_claimed = (stake.total_claimed or 0) + amount
        # ref_id 含累计领取量，避免多次领取被 ledger 幂等拦截
        self.wallet.add_redeem_points(
            user, amount, "stake_yield", "stake_claim", stake.id * 100_000 + stake.total_claimed
        )
        self.db.commit()
        return {"ok": True, "points_gained": amount}

    def unstake(self, user: User, stake_id: int) -> dict[str, Any]:
        stake = (
            self.db.query(CardStake)
            .filter(CardStake.id == stake_id, CardStake.user_id == user.id, CardStake.status == "active")
            .with_for_update()
            .first()
        )
        if not stake:
            raise NotFoundError("质押记录不存在")
        amount = self._accrued(stake)
        if amount > 0:
            stake.total_claimed = (stake.total_claimed or 0) + amount
            self.wallet.add_redeem_points(
                user, amount, "stake_yield", "stake_release", stake.id * 100_000 + stake.total_claimed
            )
        stake.status = "released"
        stake.released_at = _utcnow()
        row = self.db.get(UserCollectibleCard, stake.user_card_id)
        if row and row.lock_state == "staked":
            row.lock_state = "none"
        self.db.commit()
        return {"ok": True, "points_gained": amount}

    def list_stakes(self, user: User) -> list[dict[str, Any]]:
        rows = (
            self.db.query(CardStake, CollectibleCard)
            .join(CollectibleCard, CardStake.card_id == CollectibleCard.id)
            .filter(CardStake.user_id == user.id, CardStake.status == "active")
            .order_by(CardStake.id.desc())
            .all()
        )
        out = []
        for stake, card in rows:
            out.append(
                {
                    "stake_id": stake.id,
                    "user_card_id": stake.user_card_id,
                    "card_name": card.name,
                    "rarity": card.rarity,
                    "image_url": card.image_url,
                    "daily_yield": self._daily_yield(card.rarity),
                    "pending": self._accrued(stake),
                    "total_claimed": stake.total_claimed or 0,
                    "staked_at": stake.staked_at.isoformat() if stake.staked_at else None,
                }
            )
        return out

    # ----------------------- 竞猜加成 -----------------------
    def compute_predict_boost(self, user: User, team_ids: set[int]) -> float:
        """返回竞猜赢取加成系数（如 0.10 = +10%），上限受配置约束。

        - 质押卡所属球队命中本场 → 每张 +asset_stake_predict_boost_pct
        - 持有相关球队队徽卡 → +asset_crest_predict_boost_pct
        """
        if not team_ids:
            return 0.0
        boost = 0.0
        staked = (
            self.db.query(CardStake, CollectibleCard)
            .join(CollectibleCard, CardStake.card_id == CollectibleCard.id)
            .filter(CardStake.user_id == user.id, CardStake.status == "active")
            .all()
        )
        for _stake, card in staked:
            if card.team_id and card.team_id in team_ids:
                boost += self.settings.asset_stake_predict_boost_pct
        crests = (
            self.db.query(CollectibleCard)
            .join(UserCollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.series == "team_crest",
                CollectibleCard.team_id.in_(team_ids),
            )
            .all()
        )
        for _c in crests:
            boost += self.settings.asset_crest_predict_boost_pct
        return min(boost, self.settings.asset_predict_boost_cap_pct)
