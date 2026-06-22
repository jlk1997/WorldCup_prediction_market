"""Agent 资产/卡牌对决工具（需登录用户上下文）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.commerce import User
from app.services.agent_asset_context import AgentAssetContextService
from app.services.card_duel_service import CardDuelService


class AgentAssetTools:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _user(self) -> User | None:
        return self.db.get(User, self.user_id)

    def get_user_asset_summary(self) -> dict:
        user = self._user()
        if not user:
            return {"error": "用户不存在"}
        ctx = AgentAssetContextService(self.db).build(user, None)
        try:
            stats = CardDuelService(self.db).duel_stats(user)
            ctx["duel_record"] = {
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": stats["win_rate"],
                "elo_tier": stats["elo_tier"],
            }
        except Exception:
            pass
        ctx["disclaimer"] = (
            "球星卡为站内虚拟藏品，无现金价值；组牌与挂牌建议仅供娱乐，勿宣传投资保值。"
        )
        return ctx

    def recommend_duel_deck(self) -> dict:
        user = self._user()
        if not user:
            return {"error": "用户不存在"}
        try:
            rec = CardDuelService(self.db).recommend_deck(user)
            return {
                "card_ids": rec.get("card_ids"),
                "cards": rec.get("cards") or [],
                "avg_bp": rec.get("avg_bp"),
                "chemistry": rec.get("chemistry") or [],
                "reason": rec.get("reason"),
                "action_hint": "用户可在擂台 /arena#duel 使用智能组牌或手动选这 3 张卡出战",
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_user_duel_stats(self) -> dict:
        user = self._user()
        if not user:
            return {"error": "用户不存在"}
        stats = CardDuelService(self.db).duel_stats(user)
        return {
            **stats,
            "action_hint": "练习与快速匹配入口：擂台卡牌对决 /arena#duel",
        }

    def get_duel_elo_leaderboard(self, limit: int = 10) -> dict:
        items = CardDuelService(self.db).duel_leaderboard(limit=min(limit, 20), by="elo")
        return {"items": items, "board": "duel_elo"}

    def get_user_market_hints(self, limit: int = 5) -> dict:
        """可交易卡牌的挂牌参考（地板价/官方回购，仅供娱乐）。"""
        from app.db.models.commerce import CollectibleCard, UserCollectibleCard
        from app.services.marketplace_service import MarketplaceService

        user = self._user()
        if not user:
            return {"error": "用户不存在"}
        mkt = MarketplaceService(self.db)
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                UserCollectibleCard.tradable.is_(True),
            )
            .limit(15)
            .all()
        )
        hints = []
        for urow, card in rows:
            if (urow.count or 1) > 1:
                continue
            if urow.lock_state and urow.lock_state != "none":
                continue
            market = mkt.card_market_data(card.id)
            floor = market.get("floor_price")
            buyback = market.get("buyback_floor")
            suggest = floor if floor else buyback
            hints.append(
                {
                    "user_card_id": urow.id,
                    "card_name": card.name,
                    "rarity": card.rarity,
                    "floor_price": floor,
                    "buyback_floor": buyback,
                    "suggest_price": suggest,
                    "active_listings": market.get("active_listings"),
                    "hint": (
                        f"同卡地板价约 {floor} 可用积分"
                        if floor
                        else f"暂无挂牌，官方回购参考 {buyback} 积分"
                    ),
                }
            )
        hints.sort(key=lambda h: (h.get("suggest_price") or 0), reverse=True)
        return {
            "items": hints[: min(limit, 10)],
            "disclaimer": "挂牌价为站内虚拟积分参考，无现金价值，勿宣传投资保值。",
            "action_hint": "用户可在交易行 /marketplace 挂牌或参与竞拍",
        }
