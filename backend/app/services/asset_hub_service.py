"""资产中心聚合：待办徽章、挂牌建议（UX）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import CardDuel, CardListing, MintEvent, User, UserCollectibleCard
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

    def hub_summary(self, user: User) -> dict[str, Any]:
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
            "disclaimer": "建议价仅供站内收藏体验参考，无现金价值、不构成投资建议。",
        }
