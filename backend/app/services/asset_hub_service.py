"""资产中心聚合：待办徽章、挂牌建议（UX）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data.asset_catalog import ACHIEVEMENTS
from app.db.models.commerce import CardDuel, CardListing, CardStake, MintEvent, User, UserAchievement
from app.services.card_asset_service import CardAssetService
from app.services.card_duel_service import CardDuelService
from app.services.card_stake_service import CardStakeService
from app.services.card_transfer_service import CardTransferService
from app.services.fantasy_service import FantasyService
from app.services.marketplace_service import MarketplaceService
from app.services.primary_mint_service import PrimaryMintService


class AssetHubService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def hub_summary(self, user: User, *, light: bool = False) -> dict[str, Any]:
        if light:
            return self._hub_todo_counts(user)
        stakes = CardStakeService(self.db).list_stakes(user)
        claimable_stake = sum(int(s.get("pending") or 0) for s in stakes)
        listings = MarketplaceService(self.db).my_listings(user)
        incoming = len(CardDuelService(self.db).pending_duels(user))
        outgoing = len(CardDuelService(self.db).outgoing_duels(user))
        live_mints = (
            self.db.query(func.count(MintEvent.id))
            .filter(MintEvent.active.is_(True), MintEvent.status == "live")
            .scalar()
            or 0
        )
        rank_info = FantasyService(self.db).user_rank(user)
        asset = CardAssetService(self.db)
        achievements = asset.list_achievements(user)
        unlocked = sum(1 for a in achievements if a.get("unlocked"))
        return {
            "redeem_points": user.redeem_points or 0,
            "fan_coins": user.fan_coins or 0,
            "portfolio_value": asset.portfolio_value(user.id),
            "real_name_verified": bool(user.real_name_verified),
            "claimable_stake_points": claimable_stake,
            "active_stakes": len(stakes),
            "active_listings": len(listings),
            "duel_pending_incoming": incoming,
            "duel_pending_outgoing": outgoing,
            "live_mint_events": int(live_mints),
            "fantasy_score": int(rank_info.get("score") or 0),
            "fantasy_rank": rank_info.get("rank"),
            "achievements_unlocked": unlocked,
            "achievements_total": len(achievements),
            "action_count": sum(
                1
                for n in [
                    claimable_stake > 0,
                    incoming > 0,
                    outgoing > 0,
                    live_mints > 0,
                ]
                if n
            ),
        }

    def _hub_todo_counts(self, user: User) -> dict[str, Any]:
        """轻量 hub 聚合：今日主场用，避免全量质押/成就列表与组合估值。"""
        stake_svc = CardStakeService(self.db)
        stakes = (
            self.db.query(CardStake)
            .filter(CardStake.user_id == user.id, CardStake.status == "active")
            .all()
        )
        claimable_stake = sum(int(stake_svc._accrued(s)) for s in stakes)
        active_listings = (
            self.db.query(func.count(CardListing.id))
            .filter(CardListing.seller_id == user.id, CardListing.status == "active")
            .scalar()
            or 0
        )
        incoming = (
            self.db.query(func.count(CardDuel.id))
            .filter(
                CardDuel.defender_id == user.id,
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
            )
            .scalar()
            or 0
        )
        outgoing = (
            self.db.query(func.count(CardDuel.id))
            .filter(
                CardDuel.challenger_id == user.id,
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
            )
            .scalar()
            or 0
        )
        live_mints = (
            self.db.query(func.count(MintEvent.id))
            .filter(MintEvent.active.is_(True), MintEvent.status == "live")
            .scalar()
            or 0
        )
        rank_info = FantasyService(self.db).user_rank(user)
        achievements_unlocked = (
            self.db.query(func.count(UserAchievement.id))
            .filter(UserAchievement.user_id == user.id)
            .scalar()
            or 0
        )
        return {
            "redeem_points": user.redeem_points or 0,
            "fan_coins": user.fan_coins or 0,
            "portfolio_value": 0,
            "real_name_verified": bool(user.real_name_verified),
            "claimable_stake_points": claimable_stake,
            "active_stakes": len(stakes),
            "active_listings": int(active_listings),
            "duel_pending_incoming": int(incoming),
            "duel_pending_outgoing": int(outgoing),
            "live_mint_events": int(live_mints),
            "fantasy_score": int(rank_info.get("score") or 0),
            "fantasy_rank": rank_info.get("rank"),
            "achievements_unlocked": int(achievements_unlocked),
            "achievements_total": len(ACHIEVEMENTS),
            "action_count": sum(
                1
                for n in [
                    claimable_stake > 0,
                    incoming > 0,
                    outgoing > 0,
                    live_mints > 0,
                ]
                if n
            ),
        }

    def listing_hint(self, user: User, user_card_id: int) -> dict[str, Any]:
        """挂牌参考价：地板价、估值、建议区间（合规积分计价）。"""
        asset = CardAssetService(self.db)
        from app.db.models.commerce import CollectibleCard

        row = asset.owned_row(user, user_card_id)
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("卡牌不存在")

        market = MarketplaceService(self.db).card_market_data(card.id)
        floor = market.get("floor_price")
        last = market.get("last_price")
        buyback = CardTransferService(self.db).buyback_quote(card.rarity, row.star or 1)
        est = asset.card_value(row, card)

        if floor and last:
            suggested = int(round((floor + last) / 2))
        elif floor:
            suggested = int(floor)
        elif last:
            suggested = int(last)
        else:
            suggested = max(est, buyback + 10)

        lo = max(
            self.settings.asset_listing_min_points,
            buyback,
            int((floor or buyback) * 0.9) if floor else buyback,
        )
        hi = min(
            self.settings.asset_listing_max_points,
            max(suggested * 2, est * 2, lo + 50),
        )
        suggested = max(lo, min(hi, suggested))

        fee_pct = int(round(self.settings.asset_market_fee_pct * 100))
        ai_note = self._listing_ai_note(floor, suggested, est, market.get("active_listings", 0))
        return {
            "user_card_id": user_card_id,
            "card_name": card.name,
            "estimated_value": est,
            "floor_price": floor,
            "last_trade_price": last,
            "buyback_floor": buyback,
            "suggested_price": suggested,
            "price_range": {"min": lo, "max": hi},
            "active_listings": market.get("active_listings", 0),
            "fee_pct": fee_pct,
            "net_after_fee": int(round(suggested * (1 - self.settings.asset_market_fee_pct))),
            "ai_note": ai_note,
            "disclaimer": "建议价仅供站内收藏体验参考，无现金价值、不构成投资建议。",
        }

    def _listing_ai_note(
        self,
        floor: int | None,
        suggested: int,
        est: int,
        active_listings: int,
    ) -> str:
        if active_listings == 0:
            return "该卡暂无活跃挂牌，可参考估值与建议价首发试探。"
        if floor and suggested <= floor * 1.05:
            return "当前建议价接近地板，适合快速出手；若想多赚可略上调并观察。"
        if suggested >= est * 1.3:
            return "建议价高于估值较多，成交可能偏慢，适合不急售的藏家。"
        return "建议价处于合理区间，可参考地板与最近成交价微调。"
