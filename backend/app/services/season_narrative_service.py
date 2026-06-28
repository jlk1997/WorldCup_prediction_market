"""赛季叙事：小组赛/淘汰赛/决赛三幕收藏系列元数据。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard

SEASON_ACTS = [
    {
        "act": "group_stage",
        "title": "第一幕 · 小组赛",
        "description": "48 队群雄逐鹿，收集小组赛系列球星卡。",
        "series_tags": ["group", "wc2026_group"],
    },
    {
        "act": "knockout",
        "title": "第二幕 · 淘汰赛",
        "description": "16 强至半决赛，关键战役限量卡陆续开放。",
        "series_tags": ["knockout", "wc2026_knockout"],
    },
    {
        "act": "final",
        "title": "第三幕 · 决赛周",
        "description": "冠军之夜纪念卡与手册尊享联动。",
        "series_tags": ["final", "wc2026_final"],
    },
]


class SeasonNarrativeService:
    def __init__(self, db: Session):
        self.db = db

    def narrative_status(self, user: User | None = None) -> dict[str, Any]:
        acts: list[dict[str, Any]] = []
        for act in SEASON_ACTS:
            total = (
                self.db.query(CollectibleCard)
                .filter(CollectibleCard.series.in_(act["series_tags"]))
                .count()
            )
            owned = 0
            if user:
                owned = (
                    self.db.query(UserCollectibleCard)
                    .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
                    .filter(
                        UserCollectibleCard.user_id == user.id,
                        CollectibleCard.series.in_(act["series_tags"]),
                    )
                    .count()
                )
            acts.append(
                {
                    **act,
                    "cards_total": total,
                    "cards_owned": owned,
                    "progress_pct": round(owned / total * 100, 1) if total else 0,
                }
            )
        return {"acts": acts, "current_act": "group_stage"}
