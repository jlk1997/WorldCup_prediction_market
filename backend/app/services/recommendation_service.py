from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Match, PlayerDetailed, Team
from app.db.models.commerce import User, UserFavoritePlayer
from app.db.repositories.match_repository import MatchRepository
from app.services.profile_service import ProfileService

CHEER_HOURS_BEFORE = 24


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.core.match_kickoff import parse_kickoff


def _match_brief(m: Match, settings) -> dict:
    kick = parse_kickoff(m)
    now = _utcnow()
    close_min = settings.predict_close_minutes_before
    can_predict = m.status in (None, "scheduled") and (not kick or kick - timedelta(minutes=close_min) > now)
    can_cheer = can_predict and kick and (kick - now) <= timedelta(hours=CHEER_HOURS_BEFORE)
    return {
        "id": m.id,
        "team1": m.team1_name,
        "team2": m.team2_name,
        "date": m.match_date,
        "time": m.match_time,
        "group": m.group_name,
        "status": m.status or "scheduled",
        "can_predict": can_predict,
        "can_cheer": bool(can_cheer),
    }


def match_to_brief(m: Match, settings) -> dict:
    """Public wrapper for match brief used by game + profile routes."""
    return _match_brief(m, settings)


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.matches = MatchRepository(db)
        self.settings = get_settings()

    def get_recommendations(self, user: User | None) -> dict:
        if not user:
            return {"cta": [], "fan_identity": None}

        profile = ProfileService(self.db).get_status(user)
        main_id = user.favorite_team_id
        sub_id = user.secondary_team_id
        next_main = self._next_match_for_team(main_id) if main_id else None
        next_sub = self._next_match_for_team(sub_id) if sub_id else None
        star_matches = self._star_player_matches(user.id)

        cta: list[dict] = []
        if not user.profile_completed:
            cta.append({"type": "onboarding", "label": "完善球迷档案", "path": "/onboarding"})
        if next_main:
            mb = _match_brief(next_main, self.settings)
            cta.append(
                {
                    "type": "predict",
                    "label": f"主队 {next_main.team1_name} vs {next_main.team2_name} 竞猜",
                    "path": f"/predict?highlight={next_main.id}",
                }
            )
            if mb["can_cheer"]:
                team = self.db.get(Team, main_id)
                cta.append(
                    {
                        "type": "cheer",
                        "label": f"为 {team.name if team else '主队'} 助威",
                        "path": f"/cheer/{next_main.id}",
                    }
                )
            cta.append(
                {
                    "type": "arena",
                    "label": "去擂台为国家队助威",
                    "path": "/arena",
                }
            )
            cta.append(
                {
                    "type": "agent",
                    "label": "AI 分析主队比赛",
                    "path": f"/agent/{next_main.team1_name}/{next_main.team2_name}",
                }
            )

        return {
            "next_main_match": _match_brief(next_main, self.settings) if next_main else None,
            "next_sub_match": _match_brief(next_sub, self.settings) if next_sub else None,
            "star_player_matches": star_matches,
            "cta": cta[:6],
            "fan_identity": {
                "main_team": profile["main_team"],
                "secondary_team": profile["secondary_team"],
                "players": profile["players"],
                "fan_level": profile["fan_level"],
                "cheers_total": profile["fan_cheers_total"],
                "profile_completed": profile["profile_completed"],
            },
        }

    def _next_match_for_team(self, team_id: int) -> Match | None:
        team = self.db.get(Team, team_id)
        if not team:
            return None
        name = team.name
        rows = (
            self.db.query(Match)
            .filter(
                or_(Match.team1_name == name, Match.team2_name == name),
                or_(Match.status == "scheduled", Match.status.is_(None), Match.status == "live"),
            )
            .order_by(Match.match_date, Match.match_time)
            .all()
        )
        now = _utcnow()
        for m in rows:
            kick = parse_kickoff(m)
            if m.status == "live":
                return m
            if kick and kick >= now - timedelta(hours=2):
                return m
            if not kick:
                return m
        return rows[0] if rows else None

    def _star_player_matches(self, user_id: int) -> list[dict]:
        favs = (
            self.db.query(UserFavoritePlayer)
            .filter(UserFavoritePlayer.user_id == user_id)
            .order_by(UserFavoritePlayer.sort_order)
            .all()
        )
        out = []
        for fp in favs:
            player = self.db.get(PlayerDetailed, fp.player_id)
            if not player:
                continue
            team = self.db.get(Team, player.team_id)
            if not team:
                continue
            nxt = self._next_match_for_team(team.id)
            if nxt:
                out.append(
                    {
                        "player_name": player.name,
                        "match_id": nxt.id,
                        "team": team.name,
                        "team1": nxt.team1_name,
                        "team2": nxt.team2_name,
                    }
                )
        return out

    def is_match_day_for_user(self, user: User, today) -> bool:
        if not user.favorite_team_id:
            return False
        team = self.db.get(Team, user.favorite_team_id)
        if not team:
            return False
        today_str = today.isoformat() if hasattr(today, "isoformat") else str(today)
        row = (
            self.db.query(Match.id)
            .filter(
                or_(Match.team1_name == team.name, Match.team2_name == team.name),
                Match.match_date == today_str,
            )
            .first()
        )
        return row is not None
