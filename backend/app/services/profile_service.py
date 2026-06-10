from functools import lru_cache
from time import time

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models import PlayerDetailed, Team
from app.db.models.commerce import User, UserFavoritePlayer
from app.db.repositories.team_repository import TeamRepository

MAX_FAVORITE_PLAYERS = 3
_teams_cache: tuple[float, list[dict]] | None = None
_TEAMS_CACHE_TTL = 600


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.teams = TeamRepository(db)

    def get_status(self, user: User) -> dict:
        players = self._get_favorite_players(user.id)
        missing = []
        if not user.favorite_team_id:
            missing.append("main_team")
        if len(players) < 1:
            missing.append("players")
        main_team = self._team_brief(user.favorite_team_id)
        sub_team = self._team_brief(user.secondary_team_id)
        return {
            "profile_completed": bool(user.profile_completed),
            "main_team": main_team,
            "secondary_team": sub_team,
            "players": players,
            "missing_steps": missing,
            "fan_cheers_total": user.fan_cheers_total or 0,
            "fan_level": user.fan_level or 1,
        }

    def list_teams(self) -> list[dict]:
        global _teams_cache
        now = time()
        if _teams_cache and now - _teams_cache[0] < _TEAMS_CACHE_TTL:
            return _teams_cache[1]
        rows = self.teams.list_all()
        data = [
            {
                "id": t.id,
                "name": t.name,
                "group_name": t.group_name,
                "country_code": t.country_code,
                "logo_url": t.logo_url,
                "fifa_ranking": t.fifa_ranking,
            }
            for t in rows
        ]
        _teams_cache = (now, data)
        return data

    def list_players_for_teams(self, team_ids: list[int]) -> list[dict]:
        if not team_ids:
            return []
        ids = list({i for i in team_ids if i > 0})[:2]
        rows = (
            self.db.query(PlayerDetailed)
            .filter(PlayerDetailed.team_id.in_(ids))
            .order_by(PlayerDetailed.is_starter.desc(), PlayerDetailed.overall_rating.desc().nullslast())
            .all()
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "position": p.position,
                "team_id": p.team_id,
                "is_starter": p.is_starter,
                "overall_rating": p.overall_rating,
            }
            for p in rows
        ]

    def setup_profile(
        self,
        user: User,
        main_team_id: int,
        secondary_team_id: int | None,
        player_ids: list[int],
    ) -> dict:
        self._apply_profile(user, main_team_id, secondary_team_id, player_ids, mark_completed=True)
        return self.get_status(user)

    def update_profile(
        self,
        user: User,
        main_team_id: int | None = None,
        secondary_team_id: int | None = None,
        player_ids: list[int] | None = None,
    ) -> dict:
        main = main_team_id if main_team_id is not None else user.favorite_team_id
        sub = secondary_team_id if secondary_team_id is not None else user.secondary_team_id
        if main is None:
            raise BadRequestError("请选择主队")
        pids = player_ids if player_ids is not None else [fp.player_id for fp in self._query_fav_rows(user.id)]
        self._apply_profile(user, main, sub, pids, mark_completed=user.profile_completed or bool(main))
        return self.get_status(user)

    def _apply_profile(
        self,
        user: User,
        main_team_id: int,
        secondary_team_id: int | None,
        player_ids: list[int],
        mark_completed: bool,
    ) -> None:
        if not self.db.get(Team, main_team_id):
            raise NotFoundError("主队不存在")
        if secondary_team_id and secondary_team_id == main_team_id:
            raise BadRequestError("副队不能与主队相同")
        if secondary_team_id and not self.db.get(Team, secondary_team_id):
            raise NotFoundError("副队不存在")

        pids = list(dict.fromkeys(player_ids))[:MAX_FAVORITE_PLAYERS]
        allowed_team_ids = {main_team_id}
        if secondary_team_id:
            allowed_team_ids.add(secondary_team_id)
        for pid in pids:
            player = self.db.get(PlayerDetailed, pid)
            if not player or player.team_id not in allowed_team_ids:
                raise BadRequestError(f"球星 ID {pid} 不属于所选球队")

        user.favorite_team_id = main_team_id
        user.secondary_team_id = secondary_team_id if secondary_team_id else None
        was_completed = user.profile_completed
        if mark_completed:
            user.profile_completed = True

        self.db.query(UserFavoritePlayer).filter(UserFavoritePlayer.user_id == user.id).delete()
        for idx, pid in enumerate(pids, start=1):
            self.db.add(UserFavoritePlayer(user_id=user.id, player_id=pid, sort_order=idx))
        self.db.commit()
        self.db.refresh(user)
        if mark_completed and not was_completed:
            try:
                from app.services.referral_service import ReferralService

                ReferralService(self.db).on_profile_completed(user)
            except Exception:
                import logging

                logging.getLogger(__name__).exception("Referral profile hook failed")

    def _query_fav_rows(self, user_id: int) -> list[UserFavoritePlayer]:
        return (
            self.db.query(UserFavoritePlayer)
            .filter(UserFavoritePlayer.user_id == user_id)
            .order_by(UserFavoritePlayer.sort_order)
            .all()
        )

    def _get_favorite_players(self, user_id: int) -> list[dict]:
        rows = self._query_fav_rows(user_id)
        out = []
        for fp in rows:
            p = self.db.get(PlayerDetailed, fp.player_id)
            if p:
                out.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "position": p.position,
                        "team_id": p.team_id,
                        "sort_order": fp.sort_order,
                    }
                )
        return out

    def _team_brief(self, team_id: int | None) -> dict | None:
        if not team_id:
            return None
        t = self.db.get(Team, team_id)
        if not t:
            return None
        return {"id": t.id, "name": t.name, "group_name": t.group_name, "logo_url": t.logo_url}

    def require_profile(self, user: User) -> None:
        if not user.profile_completed:
            raise BadRequestError("请先完善球迷档案（选择主队与球星）")
