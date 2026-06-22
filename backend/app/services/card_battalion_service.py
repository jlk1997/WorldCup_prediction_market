"""卡牌持有 → 军团助威加成。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import CardStake, CollectibleCard, User, UserCollectibleCard


class CardBattalionService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def compute_battalion_card_boost(self, user: User, team_id: int | None) -> float:
        """返回助威军团点数加成比例（如 0.09 = +9%）。"""
        if not team_id:
            return 0.0
        boost = 0.0
        crest_cap = 0.09
        stake_cap = 0.15
        legend_extra = 0.02

        crests = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.series == "team_crest",
                CollectibleCard.team_id == team_id,
            )
            .all()
        )
        boost += min(len(crests) * 0.03, crest_cap)

        staked = (
            self.db.query(CardStake, CollectibleCard)
            .join(CollectibleCard, CardStake.card_id == CollectibleCard.id)
            .filter(
                CardStake.user_id == user.id,
                CardStake.status == "active",
                CollectibleCard.team_id == team_id,
            )
            .all()
        )
        boost += min(len(staked) * 0.05, stake_cap)

        legends = (
            self.db.query(UserCollectibleCard.id)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.team_id == team_id,
                CollectibleCard.rarity == "legend",
            )
            .limit(1)
            .first()
        )
        if legends:
            boost += legend_extra

        return min(boost, 0.25)

    def summary_for_user(self, user: User) -> list[dict]:
        """按球队汇总卡牌军团加成（用于我的资产页）。"""
        team_ids: set[int] = set()
        rows = (
            self.db.query(CollectibleCard.team_id)
            .join(UserCollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user.id, CollectibleCard.team_id.isnot(None))
            .distinct()
            .all()
        )
        for (tid,) in rows:
            if tid:
                team_ids.add(tid)
        from app.db.models import Team

        out = []
        for tid in sorted(team_ids):
            team = self.db.get(Team, tid)
            pct = self.compute_battalion_card_boost(user, tid)
            if pct <= 0:
                continue
            out.append(
                {
                    "team_id": tid,
                    "team_name": team.name if team else str(tid),
                    "boost_pct": round(pct * 100, 1),
                }
            )
        return sorted(out, key=lambda x: -x["boost_pct"])
