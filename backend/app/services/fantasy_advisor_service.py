"""Fantasy 阵容顾问：基于持卡与对决战力推荐 5 人阵容（仅供参考）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.services.card_asset_service import CardAssetService
from app.services.card_duel_service import CardDuelService
from app.services.fantasy_service import FantasyService


class FantasyAdvisorService:
    def __init__(self, db: Session):
        self.db = db
        self.duel = CardDuelService(db)

    def recommend_lineup(self, user: User, *, match_id: int | None = None) -> dict[str, Any]:
        asset = CardAssetService(self.db)
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                UserCollectibleCard.tradable.is_(True),
            )
            .all()
        )
        if len(rows) < 5:
            return {
                "ok": False,
                "reason": "至少需要 5 张可出战球星卡",
                "disclaimer": "仅供娱乐参考，不构成投资建议。",
            }

        scored: list[tuple[float, dict[str, Any]]] = []
        for uc, card in rows:
            val = asset.card_value(uc, card)
            bp = self.duel._card_power(uc, card)
            score = val * 0.4 + bp * 0.6
            scored.append(
                (
                    score,
                    {
                        "user_card_id": uc.id,
                        "card_id": card.id,
                        "name": card.name,
                        "rarity": card.rarity,
                        "battle_power": bp,
                        "star": uc.star,
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        picks = [x[1] for x in scored[:5]]
        rank = FantasyService(self.db).user_rank(user)
        return {
            "ok": True,
            "match_id": match_id,
            "recommended": picks,
            "summary": f"按战力与估值综合，推荐 {picks[0]['name']} 等 5 张卡组成本周阵容。",
            "fantasy_rank": rank.get("rank"),
            "fantasy_score": rank.get("score"),
            "disclaimer": "仅供娱乐参考，不构成投资建议。",
        }
