"""卡牌对决排位赛季服务。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import DuelSeason, DuelSeasonStat, User
from app.services.duel_elo_service import elo_tier

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DuelSeasonService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_active_season(self) -> DuelSeason | None:
        now = _utcnow()
        return (
            self.db.query(DuelSeason)
            .filter(
                DuelSeason.status == "active",
                DuelSeason.starts_at <= now,
                DuelSeason.ends_at >= now,
            )
            .order_by(DuelSeason.id.desc())
            .first()
        )

    def get_current_season_public(self) -> dict[str, Any]:
        season = self.get_active_season()
        if not season:
            return {"active": False}
        now = _utcnow()
        days_left = max(0, (season.ends_at - now).days)
        return {
            "active": True,
            "season_id": season.id,
            "name": season.name,
            "starts_at": season.starts_at.isoformat(),
            "ends_at": season.ends_at.isoformat(),
            "days_left": days_left,
            "reward_json": season.reward_json or {},
        }

    def record_duel_result(
        self,
        challenger: User,
        defender: User | None,
        *,
        winner_id: int,
        duel_id: int,
    ) -> None:
        if not defender:
            return
        season = self.get_active_season()
        if not season:
            return
        for user in (challenger, defender):
            if not user:
                continue
            stat = self._get_or_create_stat(user.id, season.id)
            stat.games = (stat.games or 0) + 1
            if user.id == winner_id:
                stat.wins = (stat.wins or 0) + 1
            stat.elo = int(getattr(user, "duel_elo", None) or 1000)
            stat.tier = elo_tier(stat.elo).get("code", "bronze")
            stat.updated_at = _utcnow()
        try:
            from app.services.product_analytics_service import ProductAnalyticsService

            winner = challenger if winner_id == challenger.id else defender
            tier = elo_tier(int(getattr(winner, "duel_elo", None) or 1000))
            ProductAnalyticsService(self.db).track(
                "duel_complete",
                user_id=winner_id,
                payload={"duel_id": duel_id, "season_id": season.id, "tier": tier.get("code")},
                commit=False,
            )
        except Exception:
            logger.debug("duel_complete analytics skipped")

    def _get_or_create_stat(self, user_id: int, season_id: int) -> DuelSeasonStat:
        row = (
            self.db.query(DuelSeasonStat)
            .filter(DuelSeasonStat.user_id == user_id, DuelSeasonStat.season_id == season_id)
            .first()
        )
        if row:
            return row
        row = DuelSeasonStat(user_id=user_id, season_id=season_id, elo=1000, tier="bronze")
        self.db.add(row)
        self.db.flush()
        return row

    def season_leaderboard(self, season_id: int | None = None, limit: int = 50) -> dict[str, Any]:
        season = self.db.get(DuelSeason, season_id) if season_id else self.get_active_season()
        if not season:
            return {"items": [], "season": None}
        rows = (
            self.db.query(DuelSeasonStat, User)
            .join(User, DuelSeasonStat.user_id == User.id)
            .filter(DuelSeasonStat.season_id == season.id, DuelSeasonStat.games > 0)
            .order_by(DuelSeasonStat.elo.desc(), DuelSeasonStat.wins.desc())
            .limit(min(limit, 100))
            .all()
        )
        items = []
        for rank, (stat, user) in enumerate(rows, start=1):
            tier = elo_tier(stat.elo)
            items.append(
                {
                    "rank": rank,
                    "user_id": user.id,
                    "nickname": user.nickname,
                    "elo": stat.elo,
                    "wins": stat.wins,
                    "games": stat.games,
                    "tier": tier,
                }
            )
        return {
            "season": {
                "id": season.id,
                "name": season.name,
                "ends_at": season.ends_at.isoformat(),
                "status": season.status,
            },
            "items": items,
        }

    def user_season_snapshot(self, user: User) -> dict[str, Any] | None:
        season = self.get_active_season()
        if not season:
            return None
        stat = (
            self.db.query(DuelSeasonStat)
            .filter(DuelSeasonStat.user_id == user.id, DuelSeasonStat.season_id == season.id)
            .first()
        )
        elo = int(stat.elo if stat else getattr(user, "duel_elo", None) or 1000)
        tier = elo_tier(elo)
        now = _utcnow()
        days_left = max(0, (season.ends_at - now).days)
        return {
            "season_id": season.id,
            "name": season.name,
            "days_left": days_left,
            "elo": elo,
            "wins": stat.wins if stat else 0,
            "games": stat.games if stat else 0,
            "tier": tier,
        }

    def settle_ended_seasons(self) -> dict[str, int]:
        now = _utcnow()
        seasons = (
            self.db.query(DuelSeason)
            .filter(DuelSeason.status == "active", DuelSeason.ends_at < now)
            .with_for_update()
            .all()
        )
        settled = 0
        for season in seasons:
            try:
                self._settle_one_season(season)
                season.status = "ended"
                settled += 1
            except Exception:
                logger.exception("settle duel season failed id=%s", season.id)
        if settled:
            self.db.commit()
        return {"settled": settled}

    def _settle_one_season(self, season: DuelSeason) -> None:
        rewards = season.reward_json or {}
        tier_rewards = rewards.get("tiers") or {}
        stats = (
            self.db.query(DuelSeasonStat)
            .filter(DuelSeasonStat.season_id == season.id, DuelSeasonStat.reward_claimed.is_(False))
            .all()
        )
        from app.services.collectible_service import CollectibleService

        collectible = CollectibleService(self.db)
        for stat in stats:
            if stat.games <= 0:
                continue
            user = self.db.get(User, stat.user_id)
            if not user:
                continue
            tier_cfg = tier_rewards.get(stat.tier) or tier_rewards.get("default") or {}
            points = int(tier_cfg.get("redeem_points") or 0)
            if points > 0:
                from app.db.repositories.user_repository import WalletRepository

                WalletRepository(self.db).add_redeem_points(
                    user, points, "duel_season_reward", "duel_season", season.id
                )
            if tier_cfg.get("drop"):
                collectible.drop_cards(
                    user,
                    "duel_season_reward",
                    "duel_season",
                    season.id,
                    force_rarity=tier_cfg.get("drop_rarity"),
                )
            stat.reward_claimed = True

    def create_season(
        self,
        name: str,
        starts_at: datetime,
        ends_at: datetime,
        reward_json: dict | None = None,
    ) -> DuelSeason:
        row = DuelSeason(
            name=name,
            starts_at=starts_at,
            ends_at=ends_at,
            status="active",
            reward_json=reward_json or {},
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
