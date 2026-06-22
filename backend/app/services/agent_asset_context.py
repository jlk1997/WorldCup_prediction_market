"""AI 工作台：用户球星卡资产上下文（供 Agent 分析与前端展示）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.commerce import CardDuel, CollectibleCard, User, UserCollectibleCard
from app.services.ai_billing_service import AiBillingService
from app.services.card_asset_service import CardAssetService
from app.services.card_battalion_service import CardBattalionService
from app.services.fantasy_service import FantasyService


class AgentAssetContextService:
    def __init__(self, db: Session):
        self.db = db

    def build(self, user: User, team_ids: set[int] | None = None) -> dict[str, Any]:
        """构建轻量资产摘要，供 LLM 上下文与 billing-preview 使用。"""
        asset_svc = CardAssetService(self.db)
        portfolio = asset_svc.portfolio_value(user.id)
        owned = (
            self.db.query(func.count(UserCollectibleCard.id))
            .filter(UserCollectibleCard.user_id == user.id)
            .scalar()
            or 0
        )
        billing = AiBillingService(self.db)
        discount = billing.card_discount_pct(user, team_ids)
        boost_pct = 0.0
        if user.favorite_team_id:
            boost_pct = CardBattalionService(self.db).compute_battalion_card_boost(
                user, user.favorite_team_id
            )

        fantasy_score = 0
        fantasy_rank: int | None = None
        try:
            rank_info = FantasyService(self.db).user_rank(user)
            fantasy_score = int(rank_info.get("score") or 0)
            fantasy_rank = rank_info.get("rank")
        except Exception:
            pass

        pending_duels = (
            self.db.query(func.count(CardDuel.id))
            .filter(
                CardDuel.defender_id == user.id,
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
            )
            .scalar()
            or 0
        )

        match_team_cards = 0
        if team_ids:
            match_team_cards = (
                self.db.query(func.count(UserCollectibleCard.id))
                .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
                .filter(
                    UserCollectibleCard.user_id == user.id,
                    CollectibleCard.team_id.in_(team_ids),
                )
                .scalar()
                or 0
            )

        return {
            "portfolio_value_points": portfolio,
            "redeem_points": user.redeem_points or 0,
            "fan_coins": user.fan_coins or 0,
            "cards_owned": owned,
            "match_team_cards": match_team_cards,
            "card_discount_pct": round(discount * 100, 1),
            "battalion_boost_pct": round(boost_pct * 100, 1),
            "fantasy_week_score": fantasy_score,
            "fantasy_rank": fantasy_rank,
            "pending_duel_invites": pending_duels,
            "real_name_verified": bool(user.real_name_verified),
            "disclaimer": "球星卡为站内虚拟藏品，无现金价值；分析中勿宣传投资或保值。",
        }
