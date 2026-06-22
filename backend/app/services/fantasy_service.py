"""数字阵容 Fantasy：用持有的球员卡组阵，按真实比赛表现每周积分。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.data.asset_catalog import STAR_VALUE_MULTIPLIER
from app.db.models import Match, PlayerDetailed, Team
from app.db.models.commerce import (
    CollectibleCard,
    FantasyLineup,
    FantasyScoreLog,
    FantasyWeeklySettlement,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository

logger = logging.getLogger(__name__)

GOAL_POINTS = 6
ASSIST_POINTS = 3
APPEARANCE_POINTS = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _norm(name: str) -> str:
    return "".join((name or "").lower().split())


def current_period_key(at: datetime | None = None) -> str:
    at = at or _utcnow()
    iso = at.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def previous_period_key(at: datetime | None = None) -> str:
    at = at or _utcnow()
    prev = at - timedelta(days=7)
    return current_period_key(prev)


def _period_ref_id(period_key: str) -> int:
    digits = "".join(c for c in period_key if c.isdigit())
    return int(digits[:9]) if digits else 0


class FantasyService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)

    def reward_tiers_display(self) -> list[dict[str, Any]]:
        tiers = self.settings.fantasy_reward_tier_map
        if not tiers:
            return [{"rank": 1, "coins": self.settings.fantasy_weekly_reward_coins}]
        return [{"rank": r, "coins": c} for r, c in sorted(tiers.items())]

    def eligible_cards(self, user: User) -> list[dict[str, Any]]:
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.player_id.isnot(None),
            )
            .all()
        )
        out = []
        for row, card in rows:
            if (row.count or 1) > 1:
                continue
            attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
            out.append(
                {
                    "user_card_id": row.id,
                    "card_code": card.code,
                    "name": card.name,
                    "rarity": card.rarity,
                    "image_url": card.image_url,
                    "position": attrs.get("position"),
                    "rating": attrs.get("overall_rating"),
                    "star": row.star,
                    "team_id": card.team_id,
                }
            )
        return out

    def get_lineup(self, user: User, period_key: str | None = None) -> dict[str, Any]:
        period = period_key or current_period_key()
        lineup = (
            self.db.query(FantasyLineup)
            .filter(FantasyLineup.user_id == user.id, FantasyLineup.period_key == period)
            .first()
        )
        slots: list[int] = []
        score = 0
        if lineup:
            slots = lineup.slots_json or []
            score = lineup.score or 0
        slot_cards = []
        if slots:
            rows = (
                self.db.query(UserCollectibleCard, CollectibleCard)
                .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
                .filter(UserCollectibleCard.id.in_(slots))
                .all()
            )
            by_id = {r.id: (r, c) for r, c in rows}
            for sid in slots:
                if sid in by_id:
                    row, card = by_id[sid]
                    slot_cards.append(
                        {
                            "user_card_id": row.id,
                            "name": card.name,
                            "rarity": card.rarity,
                            "image_url": card.image_url,
                            "star": row.star,
                        }
                    )
        return {
            "period_key": period,
            "size": self.settings.fantasy_lineup_size,
            "slots": slot_cards,
            "score": score,
            "weekly_reward_coins": self.settings.fantasy_weekly_reward_coins,
            "reward_tiers": self.reward_tiers_display(),
            "my_rank": self.user_rank(user, period),
        }

    def user_rank(self, user: User, period_key: str | None = None) -> dict[str, Any]:
        period = period_key or current_period_key()
        lineup = (
            self.db.query(FantasyLineup)
            .filter(FantasyLineup.user_id == user.id, FantasyLineup.period_key == period)
            .first()
        )
        score = lineup.score if lineup else 0
        if not lineup or score <= 0:
            return {"rank": None, "score": score, "on_board": False}
        higher = (
            self.db.query(FantasyLineup.id)
            .filter(
                FantasyLineup.period_key == period,
                FantasyLineup.score > score,
            )
            .count()
        )
        return {"rank": higher + 1, "score": score, "on_board": True}

    def save_lineup(self, user: User, user_card_ids: list[int]) -> dict[str, Any]:
        size = self.settings.fantasy_lineup_size
        ids = list(dict.fromkeys([int(i) for i in user_card_ids]))[:size]
        if not ids:
            raise BadRequestError("请至少选择 1 张球员卡")
        valid = (
            self.db.query(UserCollectibleCard.id)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.id.in_(ids),
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.player_id.isnot(None),
            )
            .all()
        )
        valid_ids = {v[0] for v in valid}
        if len(valid_ids) != len(ids):
            raise BadRequestError("阵容包含无效或非球员卡")

        period = current_period_key()
        lineup = (
            self.db.query(FantasyLineup)
            .filter(FantasyLineup.user_id == user.id, FantasyLineup.period_key == period)
            .with_for_update()
            .first()
        )
        if not lineup:
            lineup = FantasyLineup(user_id=user.id, period_key=period, slots_json=ids, score=0)
            self.db.add(lineup)
        else:
            lineup.slots_json = ids
        self.db.flush()
        try:
            from app.services.card_asset_service import CardAssetService

            CardAssetService(self.db).evaluate_achievements(user)
        except Exception:
            pass
        self.db.commit()
        return self.get_lineup(user, period)

    def score_logs(self, user: User, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        period = current_period_key()
        lineup = (
            self.db.query(FantasyLineup)
            .filter(FantasyLineup.user_id == user.id, FantasyLineup.period_key == period)
            .first()
        )
        if not lineup:
            return []
        logs = (
            self.db.query(FantasyScoreLog)
            .filter(FantasyScoreLog.lineup_id == lineup.id)
            .order_by(FantasyScoreLog.id.desc())
            .offset(max(0, offset))
            .limit(min(limit, 50))
            .all()
        )
        match_ids = [lg.match_id for lg in logs]
        matches: dict[int, Match] = {}
        if match_ids:
            matches = {m.id: m for m in self.db.query(Match).filter(Match.id.in_(match_ids)).all()}
        out = []
        for lg in logs:
            m = matches.get(lg.match_id)
            label = None
            if m:
                label = f"{m.team1_name or '?'} vs {m.team2_name or '?'}"
            out.append(
                {
                    "match_id": lg.match_id,
                    "match_label": label,
                    "points": lg.points,
                    "detail": lg.detail_json or {},
                    "at": lg.created_at.isoformat() if lg.created_at else None,
                }
            )
        return out

    def fantasy_me(self, user: User) -> dict[str, Any]:
        return {
            "lineup": self.get_lineup(user),
            "eligible": self.eligible_cards(user),
            "score_logs": self.score_logs(user, limit=10),
        }

    def score_match(self, match: Match) -> int:
        if match.status != "finished":
            return 0
        events = match.events_json if isinstance(match.events_json, list) else []
        scorers: dict[str, int] = {}
        assisters: dict[str, int] = {}
        for ev in events:
            if not isinstance(ev, dict):
                continue
            etype = str(ev.get("type") or ev.get("detail") or "").lower()
            player = ev.get("player") or ev.get("player_name") or ev.get("name")
            assist = ev.get("assist") or ev.get("assist_name")
            if player and "goal" in etype:
                scorers[_norm(player)] = scorers.get(_norm(player), 0) + 1
            if assist:
                assisters[_norm(assist)] = assisters.get(_norm(assist), 0) + 1

        match_teams = {_norm(match.team1_name or ""), _norm(match.team2_name or "")}
        period = current_period_key(match.live_updated_at or _utcnow())
        lineups = self.db.query(FantasyLineup).filter(FantasyLineup.period_key == period).all()
        affected = 0
        for lineup in lineups:
            slots = lineup.slots_json or []
            if not slots:
                continue
            exists = (
                self.db.query(FantasyScoreLog.id)
                .filter(FantasyScoreLog.lineup_id == lineup.id, FantasyScoreLog.match_id == match.id)
                .first()
            )
            if exists:
                continue
            pts, detail = self._score_lineup_slots(slots, scorers, assisters, match_teams)
            if pts <= 0:
                continue
            self.db.add(
                FantasyScoreLog(lineup_id=lineup.id, match_id=match.id, points=pts, detail_json=detail)
            )
            lineup.score = (lineup.score or 0) + pts
            affected += 1
        if affected:
            self.db.commit()
        return affected

    def _star_mult(self, star: int) -> float:
        return STAR_VALUE_MULTIPLIER.get(int(star or 1), 1.0)

    def _team_in_match(self, team_id: int | None, match_teams: set[str]) -> bool:
        if not team_id:
            return False
        team = self.db.get(Team, team_id)
        if not team or not team.name:
            return False
        return _norm(team.name) in match_teams

    def _score_lineup_slots(
        self,
        slots: list[int],
        scorers: dict[str, int],
        assisters: dict[str, int],
        match_teams: set[str],
    ) -> tuple[int, dict]:
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.id.in_(slots))
            .all()
        )
        total = 0
        detail: dict[str, Any] = {"players": {}}
        for row, card in rows:
            pname = None
            team_id = card.team_id
            if card.player_id:
                pd = self.db.get(PlayerDetailed, card.player_id)
                if pd:
                    pname = pd.name
                    if pd.team_id:
                        team_id = pd.team_id
            if not pname:
                pname = card.name
            key = _norm(pname)
            mult = self._star_mult(row.star)
            g = scorers.get(key, 0)
            a = assisters.get(key, 0)
            pts = int(round((g * GOAL_POINTS + a * ASSIST_POINTS) * mult))
            player_detail: dict[str, int] = {}
            if g:
                player_detail["goals"] = g
            if a:
                player_detail["assists"] = a
            if self._team_in_match(team_id, match_teams):
                app_pts = int(round(APPEARANCE_POINTS * mult))
                pts += app_pts
                player_detail["appearance"] = app_pts
            if pts:
                detail["players"][card.name] = player_detail
                total += pts
        return total, detail

    def leaderboard(self, period_key: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        period = period_key or current_period_key()
        rows = (
            self.db.query(FantasyLineup, User)
            .join(User, FantasyLineup.user_id == User.id)
            .filter(FantasyLineup.period_key == period, FantasyLineup.score > 0)
            .order_by(FantasyLineup.score.desc())
            .limit(min(limit, 50))
            .all()
        )
        out = []
        for i, (lineup, user) in enumerate(rows, start=1):
            out.append(
                {
                    "rank": i,
                    "nickname": user.nickname,
                    "score": lineup.score or 0,
                }
            )
        return out

    def settle_previous_week(self) -> dict[str, int]:
        """周一结算上周 Fantasy 周榜，发放球迷币（幂等）。"""
        period = previous_period_key()
        tiers = self.settings.fantasy_reward_tier_map
        top_n = self.settings.fantasy_reward_top_n
        ref_id = _period_ref_id(period)

        rows = (
            self.db.query(FantasyLineup, User)
            .join(User, FantasyLineup.user_id == User.id)
            .filter(FantasyLineup.period_key == period, FantasyLineup.score > 0)
            .order_by(FantasyLineup.score.desc())
            .limit(top_n)
            .all()
        )
        awarded = skipped = 0
        for rank, (lineup, user) in enumerate(rows, start=1):
            coins = tiers.get(rank, 0)
            if coins <= 0:
                skipped += 1
                continue
            exists = (
                self.db.query(FantasyWeeklySettlement.id)
                .filter(
                    FantasyWeeklySettlement.user_id == user.id,
                    FantasyWeeklySettlement.period_key == period,
                )
                .first()
            )
            if exists:
                skipped += 1
                continue
            user_locked = (
                self.db.query(User).filter(User.id == user.id).with_for_update().first()
            )
            if not user_locked:
                skipped += 1
                continue
            self.wallet.add_coins(
                user_locked, coins, "fantasy_weekly", "fantasy_period", ref_id + rank
            )
            self.db.add(
                FantasyWeeklySettlement(
                    user_id=user.id,
                    period_key=period,
                    rank=rank,
                    score=lineup.score or 0,
                    coins_awarded=coins,
                )
            )
            lineup.rewarded = True
            awarded += 1
        if awarded:
            self.db.commit()
        return {"awarded": awarded, "skipped": skipped, "period": period}
