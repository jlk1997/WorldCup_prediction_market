"""Arena battalion / star heat aggregation and leaderboard reads."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import cache_delete_prefix, cache_get, cache_set
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models import Match, PlayerDetailed, Team
from app.db.models.commerce import (
    FanActivityLog,
    GamePrediction,
    PlayerHeatDaily,
    TeamArenaSnapshot,
    TeamPowerDaily,
    User,
    UserBadge,
    UserCheer,
    UserFavoritePlayer,
    UserStarHeat,
)
from app.db.repositories.user_repository import WalletRepository
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

TIER_LABELS = {
    "pioneer": "先锋",
    "starter": "主力",
    "bench": "替补",
    "rookie": "新兵",
}

MATCHDAY_GOALS = [500, 2000, 5000]
MATCHDAY_REWARDS = [5, 10, 15]
MATCHDAY_TIER_TITLES = ["动员新星", "铁粉狂潮", "军团传奇"]

BOOST_STAR_COST = 3
BOOST_STAR_HEAT = 8
BOOST_STAR_BATTALION = 5
BOOST_CHEER_EXTRA_COST = 10
BOOST_CHEER_EXTRA_BATTALION = 20
MATCHDAY_RALLY_COST = 20
MATCHDAY_RALLY_BATTALION = 30

CHEER_POINTS_LOYAL = 10
CHEER_POINTS_NEUTRAL = 5
CHEER_BATTALION_LOYAL = 10
CHEER_BATTALION_NEUTRAL = 5

UNDERDOG_BATTALION_BONUS = 3
PREDICT_CHEER_COMBO_BATTALION = 5
SPOT_CHEER_COST = 1
SPOT_CHEER_BATTALION = 2
SPOT_CHEER_DAILY_LIMIT = 3
SPOT_CHEER_SLOGANS = ["加油！", "冲啊！", "必胜！", "燃起来！", "我们相信你！"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.core.match_kickoff import parse_kickoff


def _date_ref(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def _player_date_ref(player_id: int, d: date) -> int:
    return player_id * 100000 + _date_ref(d)


def _team_date_ref(team_id: int, d: date) -> int:
    return team_id * 100000000 + _date_ref(d)


def _spot_slot_ref(d: date, slot: int) -> int:
    return _date_ref(d) * 100 + slot


def cheer_affiliation(user: User | None, team_id: int | None) -> str:
    if not user or not team_id:
        return "neutral"
    if team_id == user.favorite_team_id:
        return "primary"
    if team_id == user.secondary_team_id:
        return "secondary"
    return "neutral"


def cheer_rewards_for_affiliation(affiliation: str) -> tuple[int, int]:
    """Return (cheer_points, battalion_delta)."""
    if affiliation in ("primary", "secondary"):
        return CHEER_POINTS_LOYAL, CHEER_BATTALION_LOYAL
    return CHEER_POINTS_NEUTRAL, CHEER_BATTALION_NEUTRAL


class ArenaService:
    CACHE_TTL = 60

    def __init__(self, db: Session):
        self.db = db
        self.wallet = WalletRepository(db)

    def record_activity(
        self,
        user: User,
        activity_type: str,
        *,
        team_id: int | None = None,
        player_id: int | None = None,
        battalion_delta: int = 0,
        star_heat_delta: int = 0,
        coins_spent: int = 0,
        ref_type: str | None = None,
        ref_id: int | None = None,
    ) -> bool:
        """Append activity log and update rollups. Returns False if duplicate."""
        if battalion_delta == 0 and star_heat_delta == 0:
            return False
        if ref_type is not None and ref_id is not None:
            dup = (
                self.db.query(FanActivityLog.id)
                .filter(
                    FanActivityLog.user_id == user.id,
                    FanActivityLog.activity_type == activity_type,
                    FanActivityLog.ref_type == ref_type,
                    FanActivityLog.ref_id == ref_id,
                )
                .first()
            )
            if dup:
                return False
        log = FanActivityLog(
            user_id=user.id,
            team_id=team_id or user.favorite_team_id,
            player_id=player_id,
            activity_type=activity_type,
            battalion_delta=battalion_delta,
            star_heat_delta=star_heat_delta,
            coins_spent=coins_spent,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        self.db.add(log)
        try:
            with self.db.begin_nested():
                self.db.flush()
        except IntegrityError:
            return False

        if battalion_delta:
            user.battalion_points_season = (user.battalion_points_season or 0) + battalion_delta
        if team_id and battalion_delta:
            self._inc_team_power(team_id, battalion_delta, user.id)
        if player_id and star_heat_delta:
            self._inc_player_heat(player_id, star_heat_delta, user.id, coins_spent > 0)
        cache_delete_prefix("arena:")
        return True

    def on_signin(self, user: User, today: date, match_day: bool) -> dict:
        if not match_day:
            return {"battalion_added": 0, "star_heat_added": 0}
        battalion = 15
        recorded = self.record_activity(
            user,
            "signin",
            team_id=user.favorite_team_id,
            battalion_delta=battalion,
            ref_type="date",
            ref_id=_date_ref(today),
        )
        star_bonus = 0
        if match_day and user.favorite_team_id:
            for fp in self._fav_players(user.id):
                if self._player_has_match_today(fp.player_id, today):
                    if self.record_activity(
                        user,
                        "signin_star",
                        team_id=user.favorite_team_id,
                        player_id=fp.player_id,
                        star_heat_delta=5,
                        ref_type="date_player",
                        ref_id=_player_date_ref(fp.player_id, today),
                    ):
                        star_bonus += 5
        return {"battalion_added": battalion if recorded else 0, "star_heat_added": star_bonus}

    def on_cheer(self, user: User, match_id: int, team_id: int) -> dict:
        affiliation = cheer_affiliation(user, team_id)
        cheer_pts, battalion = cheer_rewards_for_affiliation(affiliation)
        underdog = self._underdog_battalion_bonus(match_id, team_id)
        battalion += underdog
        star_player_id = None
        star_heat = 0
        if affiliation in ("primary", "secondary"):
            star_heat = 10
            for fp in self._fav_players(user.id):
                player = self.db.get(PlayerDetailed, fp.player_id)
                if player and player.team_id == team_id:
                    star_player_id = fp.player_id
                    break
        recorded = self.record_activity(
            user,
            "cheer",
            team_id=team_id,
            player_id=star_player_id,
            battalion_delta=battalion,
            star_heat_delta=star_heat,
            ref_type="match",
            ref_id=match_id,
        )
        return {
            "battalion_added": battalion if recorded else 0,
            "star_heat_added": star_heat if recorded else 0,
            "cheer_points": cheer_pts,
            "affiliation": affiliation,
            "underdog_bonus": underdog if recorded else 0,
        }

    def try_predict_cheer_combo(self, user: User, match_id: int) -> dict:
        pred = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.user_id == user.id, GamePrediction.match_id == match_id)
            .first()
        )
        cheer = (
            self.db.query(UserCheer)
            .filter(UserCheer.user_id == user.id, UserCheer.match_id == match_id)
            .first()
        )
        if not pred or not cheer:
            return {"battalion_added": 0, "combo_unlocked": False}
        recorded = self.record_activity(
            user,
            "predict_cheer_combo",
            team_id=cheer.team_id,
            battalion_delta=PREDICT_CHEER_COMBO_BATTALION,
            ref_type="match",
            ref_id=match_id,
        )
        return {
            "battalion_added": PREDICT_CHEER_COMBO_BATTALION if recorded else 0,
            "combo_unlocked": bool(recorded),
        }

    def _underdog_battalion_bonus(self, match_id: int, team_id: int) -> int:
        arena = self.get_match_arena(match_id, None, use_cache=False)
        home = arena["home"]
        away = arena["away"]
        if not home.get("team_id") or not away.get("team_id"):
            return 0
        hp, ap = int(home["power"] or 0), int(away["power"] or 0)
        if team_id == home["team_id"] and hp < ap:
            return UNDERDOG_BATTALION_BONUS
        if team_id == away["team_id"] and ap < hp:
            return UNDERDOG_BATTALION_BONUS
        return 0

    def underdog_bonus_for_team(self, match_id: int, team_id: int | None) -> int:
        if not team_id:
            return 0
        return self._underdog_battalion_bonus(match_id, team_id)

    def _combo_already_done(self, user_id: int, match_id: int) -> bool:
        return (
            self.db.query(FanActivityLog.id)
            .filter(
                FanActivityLog.user_id == user_id,
                FanActivityLog.activity_type == "predict_cheer_combo",
                FanActivityLog.ref_type == "match",
                FanActivityLog.ref_id == match_id,
            )
            .first()
            is not None
        )

    def on_quiz_correct(self, user: User, today: date) -> dict:
        recorded = self.record_activity(
            user,
            "quiz",
            team_id=user.favorite_team_id,
            battalion_delta=8,
            ref_type="date",
            ref_id=_date_ref(today),
        )
        return {"battalion_added": 8 if recorded else 0}

    def on_predict_submit(self, user: User, match_id: int) -> dict:
        recorded = self.record_activity(
            user,
            "predict_submit",
            team_id=user.favorite_team_id,
            battalion_delta=5,
            ref_type="match",
            ref_id=match_id,
        )
        return {"battalion_added": 5 if recorded else 0}

    def on_predict_settle(self, user: User, pred: GamePrediction, match: Match) -> dict:
        if pred.status != "won" or not pred.points_awarded:
            return {"battalion_added": 0}
        battalion = pred.points_awarded
        star_heat = 0
        fav_team_ids = {user.favorite_team_id, user.secondary_team_id} - {None}
        t1 = self._team_id_by_name(match.team1_name)
        t2 = self._team_id_by_name(match.team2_name)
        match_teams = {x for x in (t1, t2) if x}
        if fav_team_ids & match_teams:
            for fp in self._fav_players(user.id):
                player = self.db.get(PlayerDetailed, fp.player_id)
                if player and player.team_id in match_teams:
                    star_heat += int(battalion * 0.5)
                    break
        recorded = self.record_activity(
            user,
            "predict_win",
            team_id=user.favorite_team_id,
            battalion_delta=battalion,
            star_heat_delta=star_heat,
            ref_type="prediction",
            ref_id=pred.id,
        )
        return {"battalion_added": battalion if recorded else 0, "star_heat_added": star_heat if recorded else 0}

    def get_overview(self, user: User) -> dict:
        cache_key = f"arena:overview:{user.id}"
        cached = cache_get(cache_key)
        if cached:
            return cached
        standing = self.get_my_standing(user)
        next_arena = None
        if user.favorite_team_id:
            nxt = RecommendationService(self.db)._next_match_for_team(user.favorite_team_id)
            if nxt:
                next_arena = self.get_match_arena(nxt.id, user.id)
        star_summary = self.get_star_heat_board(user, scope="my", limit=3)
        goal = self.get_matchday_goal(user)
        goal_secondary = (
            self.get_matchday_goal(user, user.secondary_team_id)
            if user.secondary_team_id and user.secondary_team_id != user.favorite_team_id
            else {"active": False, "progress": 0, "goals": MATCHDAY_GOALS, "tier_reached": 0}
        )
        spot = self.get_spot_cheer_status(user)
        today_rows = self.get_today_matches(user)
        cheerable = sum(1 for m in today_rows if m.get("can_cheer") and not m.get("user_cheered"))
        combo_ops = sum(
            1
            for m in today_rows
            if m.get("predict_combo_pending") or m.get("predict_combo_after_cheer")
        )
        out = {
            "standing": standing,
            "next_match_arena": next_arena,
            "my_stars": star_summary.get("rows", [])[:3],
            "matchday_goal": goal,
            "matchday_goal_secondary": goal_secondary,
            "spot_cheer": spot,
            "quick_stats": {
                "today_matches": len(today_rows),
                "today_cheerable": cheerable,
                "spot_remaining": spot.get("remaining", 0),
                "combo_opportunities": combo_ops,
            },
        }
        cache_set(cache_key, out, self.CACHE_TTL)
        return out

    def get_team_battalion_leaderboard(
        self, team_id: int | None, period: str = "season", limit: int = 30
    ) -> list[dict]:
        cache_key = f"arena:team_rank:{team_id}:{period}:{limit}"
        cached = cache_get(cache_key)
        if cached:
            return cached
        q = self.db.query(User).filter(User.status == "active", User.favorite_team_id.isnot(None))
        if team_id:
            q = q.filter(User.favorite_team_id == team_id)
        if period in ("daily", "weekly"):
            if period == "daily":
                cutoff = datetime.combine(_utcnow().date(), datetime.min.time())
            else:
                cutoff = _utcnow() - timedelta(days=7)
            sub = (
                self.db.query(
                    FanActivityLog.user_id,
                    func.sum(FanActivityLog.battalion_delta).label("pts"),
                )
                .filter(
                    FanActivityLog.created_at >= cutoff,
                    FanActivityLog.battalion_delta > 0,
                )
            )
            if team_id:
                sub = sub.filter(FanActivityLog.team_id == team_id)
            sub = sub.group_by(FanActivityLog.user_id).subquery()
            rows_q = (
                self.db.query(User, sub.c.pts)
                .join(sub, User.id == sub.c.user_id)
                .filter(User.status == "active", User.favorite_team_id.isnot(None))
            )
            if team_id:
                rows_q = rows_q.filter(User.favorite_team_id == team_id)
            rows = rows_q.order_by(desc(sub.c.pts)).limit(limit).all()
            out = [
                {
                    "user_id": u.id,
                    "nickname": u.nickname,
                    "battalion_points": int(pts or 0),
                    "arena_tier": u.arena_tier,
                    "tier_label": TIER_LABELS.get(u.arena_tier, u.arena_tier),
                }
                for u, pts in rows
            ]
        else:
            rows = q.order_by(desc(User.battalion_points_season)).limit(limit).all()
            out = [
                {
                    "user_id": u.id,
                    "nickname": u.nickname,
                    "battalion_points": u.battalion_points_season or 0,
                    "arena_tier": u.arena_tier,
                    "tier_label": TIER_LABELS.get(u.arena_tier, u.arena_tier),
                }
                for u in rows
            ]
        cache_set(cache_key, out, self.CACHE_TTL)
        return out

    def get_team_supporter_leaderboard(
        self, team_id: int | None, period: str = "season", limit: int = 30
    ) -> list[dict]:
        """Rank users by battalion contributed *to* a team (not by favorite_team_id)."""
        if not team_id:
            return []
        cache_key = f"arena:supporter_rank:{team_id}:{period}:{limit}"
        cached = cache_get(cache_key)
        if cached:
            return cached
        sub_q = self.db.query(
            FanActivityLog.user_id,
            func.sum(FanActivityLog.battalion_delta).label("pts"),
        ).filter(
            FanActivityLog.team_id == team_id,
            FanActivityLog.battalion_delta > 0,
        )
        if period == "daily":
            cutoff = datetime.combine(_utcnow().date(), datetime.min.time())
            sub_q = sub_q.filter(FanActivityLog.created_at >= cutoff)
        elif period == "weekly":
            cutoff = _utcnow() - timedelta(days=7)
            sub_q = sub_q.filter(FanActivityLog.created_at >= cutoff)
        sub = sub_q.group_by(FanActivityLog.user_id).subquery()
        rows = (
            self.db.query(User, sub.c.pts)
            .join(sub, User.id == sub.c.user_id)
            .filter(User.status == "active")
            .order_by(desc(sub.c.pts))
            .limit(limit)
            .all()
        )
        out = [
            {
                "user_id": u.id,
                "nickname": u.nickname,
                "battalion_points": int(pts or 0),
                "favorite_team_id": u.favorite_team_id,
                "arena_tier": u.arena_tier,
                "tier_label": TIER_LABELS.get(u.arena_tier, u.arena_tier),
            }
            for u, pts in rows
        ]
        cache_set(cache_key, out, self.CACHE_TTL)
        return out

    def get_spot_cheer_status(self, user: User) -> dict:
        today = _utcnow().date()
        used = self._count_spot_cheers_today(user.id, today)
        teams = self._teams_playing_on(today)
        return {
            "daily_limit": SPOT_CHEER_DAILY_LIMIT,
            "used_today": used,
            "remaining": max(0, SPOT_CHEER_DAILY_LIMIT - used),
            "cost": SPOT_CHEER_COST,
            "battalion_per_cheer": SPOT_CHEER_BATTALION,
            "slogans": SPOT_CHEER_SLOGANS,
            "teams_today": teams,
        }

    def spot_cheer(self, user: User, team_id: int, slogan_index: int = 0) -> dict:
        from app.services.profile_service import ProfileService

        ProfileService(self.db).require_profile(user)
        today = _utcnow().date()
        if not RecommendationService(self.db).is_match_day_for_team(team_id, today):
            raise BadRequestError("所选球队今日无比赛")
        used = self._count_spot_cheers_today(user.id, today)
        if used >= SPOT_CHEER_DAILY_LIMIT:
            raise BadRequestError("今日临场口号次数已用完")
        if slogan_index < 0 or slogan_index >= len(SPOT_CHEER_SLOGANS):
            raise BadRequestError("无效口号")
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        used = self._count_spot_cheers_today(user.id, today)
        if used >= SPOT_CHEER_DAILY_LIMIT:
            raise BadRequestError("今日临场口号次数已用完")
        ref_id = _spot_slot_ref(today, used)
        self.wallet.deduct_coins(user, SPOT_CHEER_COST, "arena_spot_cheer", "team", team_id)
        ok = self.record_activity(
            user,
            "spot_cheer",
            team_id=team_id,
            battalion_delta=SPOT_CHEER_BATTALION,
            coins_spent=SPOT_CHEER_COST,
            ref_type="spot_slot",
            ref_id=ref_id,
        )
        if not ok:
            raise BadRequestError("今日临场口号次数已用完")
        self.db.commit()
        status = self.get_spot_cheer_status(user)
        return {
            "fan_coins": user.fan_coins,
            "battalion_added": SPOT_CHEER_BATTALION,
            "slogan": SPOT_CHEER_SLOGANS[slogan_index],
            "spot_cheer": status,
        }

    def _count_spot_cheers_today(self, user_id: int, today: date) -> int:
        day_base = _date_ref(today) * 100
        return (
            self.db.query(FanActivityLog.id)
            .filter(
                FanActivityLog.user_id == user_id,
                FanActivityLog.activity_type == "spot_cheer",
                FanActivityLog.ref_type == "spot_slot",
                FanActivityLog.ref_id >= day_base,
                FanActivityLog.ref_id < day_base + 100,
            )
            .count()
        )

    def _teams_playing_on(self, today: date) -> list[dict]:
        today_str = today.isoformat()
        matches = self.db.query(Match).filter(Match.match_date == today_str).all()
        seen: dict[int, str] = {}
        for m in matches:
            for name in (m.team1_name, m.team2_name):
                tid = self._team_id_by_name(name)
                if tid and tid not in seen:
                    seen[tid] = name
        return [{"team_id": tid, "team_name": name} for tid, name in sorted(seen.items(), key=lambda x: x[1])]

    def get_match_arena(self, match_id: int, user_id: int | None = None, *, use_cache: bool = True) -> dict:
        cache_key = f"arena:match:{match_id}"
        cached = cache_get(cache_key) if use_cache else None
        match = self.db.get(Match, match_id)
        if not match:
            raise NotFoundError("比赛不存在")
        t1 = self._team_id_by_name(match.team1_name)
        t2 = self._team_id_by_name(match.team2_name)
        snap = self.db.query(TeamArenaSnapshot).filter(TeamArenaSnapshot.match_id == match_id).first()
        if snap:
            home_power, away_power = snap.home_power, snap.away_power
        elif cached:
            home_power = cached["home"]["power"]
            away_power = cached["away"]["power"]
        else:
            kick = parse_kickoff(match)
            window_start = (kick - timedelta(hours=72)) if kick else _utcnow() - timedelta(hours=72)
            home_power = self._team_power_in_window(t1, window_start) if t1 else 0
            away_power = self._team_power_in_window(t2, window_start) if t2 else 0
        user_contributed = False
        if user_id and t1 and t2:
            user_contributed = (
                self.db.query(FanActivityLog.id)
                .filter(
                    FanActivityLog.user_id == user_id,
                    FanActivityLog.team_id.in_([t1, t2]),
                    FanActivityLog.battalion_delta > 0,
                )
                .first()
                is not None
            )
        lead = abs(home_power - away_power)
        leader = match.team1_name if home_power >= away_power else match.team2_name
        out = {
            "match_id": match_id,
            "team1_name": match.team1_name,
            "team2_name": match.team2_name,
            "status": match.status or "scheduled",
            "home": {"team_id": t1, "name": match.team1_name, "power": home_power},
            "away": {"team_id": t2, "name": match.team2_name, "power": away_power},
            "leader_name": leader if lead else None,
            "lead_points": lead,
            "user_contributed": user_contributed,
            "frozen": snap is not None,
        }
        if not snap and use_cache:
            cache_set(cache_key, out, self.CACHE_TTL)
        return out

    def get_star_heat_board(self, user: User | None, scope: str = "global", limit: int = 20) -> dict:
        cache_key = f"arena:star_heat:{scope}:{user.id if user else 0}:{limit}"
        cached = cache_get(cache_key)
        if cached:
            return cached
        if scope == "my" and user:
            rows = (
                self.db.query(UserStarHeat, PlayerDetailed, UserFavoritePlayer.sort_order)
                .join(PlayerDetailed, UserStarHeat.player_id == PlayerDetailed.id)
                .join(
                    UserFavoritePlayer,
                    (UserFavoritePlayer.player_id == UserStarHeat.player_id)
                    & (UserFavoritePlayer.user_id == user.id),
                )
                .filter(UserStarHeat.user_id == user.id)
                .order_by(UserFavoritePlayer.sort_order)
                .all()
            )
            global_heat = (
                self.db.query(
                    UserStarHeat.player_id,
                    func.sum(UserStarHeat.heat_total).label("total"),
                )
                .group_by(UserStarHeat.player_id)
                .subquery()
            )
            out_rows = []
            for ush, player, _ in rows:
                global_total = (
                    self.db.query(func.coalesce(func.sum(UserStarHeat.heat_total), 0))
                    .filter(UserStarHeat.player_id == player.id)
                    .scalar()
                )
                out_rows.append(
                    {
                        "player_id": player.id,
                        "player_name": player.name,
                        "team_id": player.team_id,
                        "my_heat": ush.heat_total,
                        "global_heat": int(global_total or 0),
                        "can_boost_today": self._can_boost_star(user.id, player.id),
                    }
                )
            out = {"scope": "my", "rows": out_rows}
        else:
            rows = (
                self.db.query(
                    PlayerDetailed.id,
                    PlayerDetailed.name,
                    PlayerDetailed.team_id,
                    func.coalesce(func.sum(UserStarHeat.heat_total), 0).label("heat"),
                )
                .outerjoin(UserStarHeat, UserStarHeat.player_id == PlayerDetailed.id)
                .group_by(PlayerDetailed.id, PlayerDetailed.name, PlayerDetailed.team_id)
                .order_by(desc("heat"))
                .limit(limit)
                .all()
            )
            out = {
                "scope": "global",
                "rows": [
                    {
                        "player_id": pid,
                        "player_name": name,
                        "team_id": tid,
                        "global_heat": int(heat or 0),
                    }
                    for pid, name, tid, heat in rows
                    if int(heat or 0) > 0
                ],
            }
        cache_set(cache_key, out, self.CACHE_TTL)
        return out

    def get_star_accuracy_board(self, player_id: int | None = None, limit: int = 20) -> list[dict]:
        cache_key = f"arena:star_acc:{player_id}:{limit}"
        cached = cache_get(cache_key)
        if cached:
            return cached

        from sqlalchemy import case, func

        base = (
            self.db.query(
                UserFavoritePlayer.player_id.label("player_id"),
                PlayerDetailed.name.label("player_name"),
                func.count(GamePrediction.id).label("sample_size"),
                func.sum(case((GamePrediction.status == "won", 1), else_=0)).label("wins"),
            )
            .join(PlayerDetailed, PlayerDetailed.id == UserFavoritePlayer.player_id)
            .join(Team, Team.id == PlayerDetailed.team_id)
            .join(GamePrediction, GamePrediction.user_id == UserFavoritePlayer.user_id)
            .join(
                Match,
                (Match.id == GamePrediction.match_id)
                & or_(Match.team1_name == Team.name, Match.team2_name == Team.name),
            )
            .filter(GamePrediction.status.in_(("won", "lost")))
        )
        if player_id:
            base = base.filter(UserFavoritePlayer.player_id == player_id)
        rows = (
            base.group_by(UserFavoritePlayer.player_id, PlayerDetailed.name)
            .having(func.count(GamePrediction.id) >= 3)
            .all()
        )
        ranked: list[dict] = []
        for pid, pname, sample, wins in rows:
            sample_i = int(sample or 0)
            wins_i = int(wins or 0)
            if sample_i < 3:
                continue
            ranked.append(
                {
                    "player_id": pid,
                    "player_name": pname,
                    "accuracy_pct": round(wins_i / sample_i * 100, 1),
                    "sample_size": sample_i,
                    "top_fans": [],
                }
            )
        ranked.sort(key=lambda x: x["accuracy_pct"], reverse=True)
        ranked = ranked[:limit]

        for item in ranked:
            pid = item["player_id"]
            team = (
                self.db.query(Team)
                .join(PlayerDetailed, PlayerDetailed.team_id == Team.id)
                .filter(PlayerDetailed.id == pid)
                .first()
            )
            if not team:
                continue
            user_ids = [
                r[0]
                for r in self.db.query(UserFavoritePlayer.user_id)
                .filter(UserFavoritePlayer.player_id == pid)
                .all()
            ]
            if not user_ids:
                continue
            top_users = (
                self.db.query(User.id, User.nickname, func.count(GamePrediction.id).label("cnt"))
                .join(GamePrediction, GamePrediction.user_id == User.id)
                .join(Match, Match.id == GamePrediction.match_id)
                .filter(
                    User.id.in_(user_ids),
                    GamePrediction.status == "won",
                    or_(Match.team1_name == team.name, Match.team2_name == team.name),
                )
                .group_by(User.id, User.nickname)
                .order_by(desc("cnt"))
                .limit(5)
                .all()
            )
            item["top_fans"] = [
                {"user_id": uid, "nickname": nick, "wins": cnt} for uid, nick, cnt in top_users
            ]

        cache_set(cache_key, ranked, self.CACHE_TTL)
        return ranked

    def get_matchday_goal(self, user: User, team_id: int | None = None) -> dict:
        today = _utcnow().date()
        tid = team_id or user.favorite_team_id
        if team_id is not None and team_id not in {user.favorite_team_id, user.secondary_team_id}:
            raise BadRequestError("只能查看主/副队的比赛日目标")
        inactive = {"active": False, "progress": 0, "goals": MATCHDAY_GOALS, "tier_reached": 0}
        if not tid:
            return inactive
        rec = RecommendationService(self.db)
        if not rec.is_match_day_for_team(tid, today):
            return {**inactive, "team_id": tid}
        team = self.db.get(Team, tid)
        row = (
            self.db.query(TeamPowerDaily)
            .filter(TeamPowerDaily.team_id == tid, TeamPowerDaily.stat_date == today)
            .first()
        )
        progress = row.power_total if row else 0
        tier = sum(1 for g in MATCHDAY_GOALS if progress >= g)
        day_ref = _date_ref(today)
        my_rewards = [
            b.title
            for b in self.db.query(UserBadge)
            .filter(
                UserBadge.user_id == user.id,
                UserBadge.badge_code.like(f"matchday_rally_{tid}_{day_ref}_%"),
            )
            .all()
        ]
        rally_ref = _team_date_ref(tid, today)
        rally_done = (
            self.db.query(FanActivityLog.id)
            .filter(
                FanActivityLog.user_id == user.id,
                FanActivityLog.activity_type == "matchday_rally",
                FanActivityLog.ref_type == "team_date",
                FanActivityLog.ref_id == rally_ref,
            )
            .first()
            is not None
        )
        return {
            "active": True,
            "team_id": tid,
            "team_name": team.name if team else None,
            "progress": progress,
            "goals": MATCHDAY_GOALS,
            "goal_titles": MATCHDAY_TIER_TITLES,
            "tier_reached": tier,
            "rewards_coins": MATCHDAY_REWARDS[:tier],
            "my_titles": my_rewards,
            "rally_done_today": rally_done,
        }

    def get_my_standing(self, user: User) -> dict:
        team_id = user.favorite_team_id
        if not team_id:
            return {
                "team_id": None,
                "rank": None,
                "total_members": 0,
                "battalion_points": user.battalion_points_season or 0,
                "gap_to_prev": 0,
                "arena_tier": user.arena_tier,
                "tier_label": TIER_LABELS.get(user.arena_tier, user.arena_tier),
            }
        pts = user.battalion_points_season or 0
        member_filter = (User.favorite_team_id == team_id, User.status == "active")
        total_members = self.db.scalar(
            select(func.count()).select_from(User).where(*member_filter)
        ) or 0
        rank = (
            self.db.scalar(
                select(func.count()).select_from(User).where(
                    *member_filter,
                    User.battalion_points_season > pts,
                )
            )
            or 0
        ) + 1
        gap = 0
        if rank > 1:
            prev_pts = self.db.scalar(
                select(func.min(User.battalion_points_season)).where(
                    *member_filter,
                    User.battalion_points_season > pts,
                )
            )
            gap = max(0, (prev_pts or 0) - pts)
        star_contrib = (
            self.db.query(UserStarHeat, PlayerDetailed)
            .join(PlayerDetailed, UserStarHeat.player_id == PlayerDetailed.id)
            .filter(UserStarHeat.user_id == user.id)
            .all()
        )
        return {
            "team_id": team_id,
            "rank": rank,
            "total_members": total_members,
            "battalion_points": pts,
            "gap_to_prev": gap,
            "arena_tier": user.arena_tier,
            "tier_label": TIER_LABELS.get(user.arena_tier, user.arena_tier),
            "star_contributions": [
                {"player_id": p.id, "player_name": p.name, "heat": h.heat_total} for h, p in star_contrib
            ],
        }

    def boost_star(self, user: User, player_id: int) -> dict:
        fav = (
            self.db.query(UserFavoritePlayer)
            .filter(UserFavoritePlayer.user_id == user.id, UserFavoritePlayer.player_id == player_id)
            .first()
        )
        if not fav:
            raise BadRequestError("只能应援您收藏的球星")
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        if not self._can_boost_star(user.id, player_id):
            raise BadRequestError("该球星今日已应援过")
        today = _utcnow().date()
        self.wallet.deduct_coins(user, BOOST_STAR_COST, "arena_boost_star", "player", player_id)
        ok = self.record_activity(
            user,
            "boost_star",
            team_id=user.favorite_team_id,
            player_id=player_id,
            battalion_delta=BOOST_STAR_BATTALION,
            star_heat_delta=BOOST_STAR_HEAT,
            coins_spent=BOOST_STAR_COST,
            ref_type="player_date",
            ref_id=_player_date_ref(player_id, today),
        )
        if not ok:
            raise BadRequestError("今日已应援过该球星")
        self.db.commit()
        return {"fan_coins": user.fan_coins, "star_heat_added": BOOST_STAR_HEAT, "battalion_added": BOOST_STAR_BATTALION}

    def boost_cheer_extra(self, user: User, match_id: int) -> dict:
        match = self.db.get(Match, match_id)
        if not match:
            raise NotFoundError("比赛不存在")
        kick = parse_kickoff(match)
        now = _utcnow()
        if not kick:
            raise BadRequestError("该比赛缺少开球时间，暂不可助威加码")
        from app.core.config import get_settings

        close_minutes = get_settings().predict_close_minutes_before
        if kick - timedelta(minutes=close_minutes) <= now:
            raise BadRequestError("该比赛已停止助威加码")
        if match.status not in (None, "scheduled"):
            raise BadRequestError("比赛已开始或结束")
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        uc = self.db.query(UserCheer).filter(UserCheer.user_id == user.id, UserCheer.match_id == match_id).first()
        if not uc:
            raise BadRequestError("请先完成普通助威")
        exists = (
            self.db.query(FanActivityLog)
            .filter(
                FanActivityLog.user_id == user.id,
                FanActivityLog.activity_type == "boost_cheer_extra",
                FanActivityLog.ref_type == "match",
                FanActivityLog.ref_id == match_id,
            )
            .first()
        )
        if exists:
            raise BadRequestError("本场已助威加码")
        self.wallet.deduct_coins(user, BOOST_CHEER_EXTRA_COST, "arena_cheer_extra", "match", match_id)
        ok = self.record_activity(
            user,
            "boost_cheer_extra",
            team_id=uc.team_id,
            battalion_delta=BOOST_CHEER_EXTRA_BATTALION,
            coins_spent=BOOST_CHEER_EXTRA_COST,
            ref_type="match",
            ref_id=match_id,
        )
        if not ok:
            raise BadRequestError("加码失败")
        self.db.commit()
        return {"fan_coins": user.fan_coins, "battalion_added": BOOST_CHEER_EXTRA_BATTALION}

    def matchday_rally(self, user: User, team_id: int | None = None) -> dict:
        today = _utcnow().date()
        tid = team_id or user.favorite_team_id
        if not tid:
            raise BadRequestError("请先设置主队")
        allowed = {user.favorite_team_id, user.secondary_team_id}
        if tid not in allowed:
            raise BadRequestError("只能为主队或副队动员")
        rec = RecommendationService(self.db)
        if not rec.is_match_day_for_team(tid, today):
            raise BadRequestError("所选球队今日无比赛")
        ref_id = _team_date_ref(tid, today)
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        exists = (
            self.db.query(FanActivityLog)
            .filter(
                FanActivityLog.user_id == user.id,
                FanActivityLog.activity_type == "matchday_rally",
                FanActivityLog.ref_type == "team_date",
                FanActivityLog.ref_id == ref_id,
            )
            .first()
        )
        if exists:
            raise BadRequestError("该队今日已动员过")
        self.wallet.deduct_coins(user, MATCHDAY_RALLY_COST, "arena_matchday_rally", "team", tid)
        ok = self.record_activity(
            user,
            "matchday_rally",
            team_id=tid,
            battalion_delta=MATCHDAY_RALLY_BATTALION,
            coins_spent=MATCHDAY_RALLY_COST,
            ref_type="team_date",
            ref_id=ref_id,
        )
        if not ok:
            raise BadRequestError("动员失败")
        collectible_drop = None
        try:
            from app.services.collectible_service import CollectibleService

            collectible_drop = CollectibleService(self.db).matchday_drop(user, tid)
        except Exception:
            logger.exception("Collectible matchday drop failed user=%s", user.id)
        self.db.commit()
        return {
            "fan_coins": user.fan_coins,
            "battalion_added": MATCHDAY_RALLY_BATTALION,
            "team_id": tid,
            "collectible_drop": collectible_drop,
        }

    def get_today_matches(self, user: User) -> list[dict]:
        from app.services.game_service import GameService

        today_str = _utcnow().date().isoformat()
        matches = (
            self.db.query(Match)
            .filter(Match.match_date == today_str, or_(Match.status.is_(None), Match.status == "scheduled"))
            .order_by(Match.match_time)
            .all()
        )
        gs = GameService(self.db)
        out: list[dict] = []
        for m in matches:
            status = gs.get_cheer_status(m.id, user.id)
            t1_id = status["team1"]["id"]
            t2_id = status["team2"]["id"]
            out.append(
                {
                    "match_id": m.id,
                    "match_date": m.match_date,
                    "match_time": m.match_time,
                    "team1_name": m.team1_name,
                    "team2_name": m.team2_name,
                    "team1_id": t1_id,
                    "team2_id": t2_id,
                    "team1_affiliation": cheer_affiliation(user, t1_id),
                    "team2_affiliation": cheer_affiliation(user, t2_id),
                    "team1_underdog_bonus": status["team1"].get("underdog_bonus", 0),
                    "team2_underdog_bonus": status["team2"].get("underdog_bonus", 0),
                    "can_cheer": status["can_cheer"],
                    "user_cheered": status["user_cheered"],
                    "user_cheer_team_id": status.get("user_cheer_team_id"),
                    "has_prediction": status.get("has_prediction", False),
                    "predict_combo_pending": status.get("predict_combo_pending", False),
                    "predict_combo_after_cheer": status.get("predict_combo_after_cheer", False),
                    "cheer_block_reason": status.get("cheer_block_reason"),
                    "arena": status["arena"],
                }
            )
        return out

    def recalc_arena_tiers(self, team_id: int | None = None) -> int:
        q = self.db.query(User).filter(User.status == "active", User.favorite_team_id.isnot(None))
        if team_id:
            q = q.filter(User.favorite_team_id == team_id)
        teams = {u.favorite_team_id for u in q.all()}
        updated = 0
        for tid in teams:
            members = (
                self.db.query(User)
                .filter(User.favorite_team_id == tid, User.status == "active")
                .order_by(desc(User.battalion_points_season))
                .all()
            )
            n = len(members)
            if not n:
                continue
            for i, u in enumerate(members):
                pct = (i + 1) / n
                if pct <= 0.10:
                    tier = "pioneer"
                elif pct <= 0.30:
                    tier = "starter"
                elif pct <= 0.60:
                    tier = "bench"
                else:
                    tier = "rookie"
                if u.arena_tier != tier:
                    u.arena_tier = tier
                    updated += 1
        if updated:
            self.db.commit()
            cache_delete_prefix("arena:")
        return updated

    def freeze_finished_arenas(self) -> int:
        from datetime import timedelta

        since = _utcnow() - timedelta(days=3)
        finished = (
            self.db.query(Match)
            .filter(Match.status == "finished", Match.live_updated_at >= since)
            .limit(200)
            .all()
        )
        if not finished:
            finished = self.db.query(Match).filter(Match.status == "finished").order_by(Match.id.desc()).limit(50).all()
        count = 0
        for match in finished:
            if self.db.query(TeamArenaSnapshot).filter(TeamArenaSnapshot.match_id == match.id).first():
                continue
            arena = self.get_match_arena(match.id)
            t1 = arena["home"]["team_id"]
            t2 = arena["away"]["team_id"]
            if not t1 or not t2:
                continue
            self.db.add(
                TeamArenaSnapshot(
                    match_id=match.id,
                    home_team_id=t1,
                    away_team_id=t2,
                    home_power=arena["home"]["power"],
                    away_power=arena["away"]["power"],
                )
            )
            count += 1
        if count:
            self.db.commit()
        return count

    def process_matchday_goal_rewards(self) -> int:
        """Award coins + virtual badges when team daily power hits rally tiers."""
        from app.core.distributed_lock import distributed_lock

        today = _utcnow().date()
        lock_key = f"ingest:matchday_rewards:{today.isoformat()}"
        with distributed_lock(lock_key, ttl_sec=600) as acquired:
            if not acquired:
                return 0
            return self._process_matchday_goal_rewards_locked(today)

    def _process_matchday_goal_rewards_locked(self, today: date) -> int:
        today_str = today.isoformat()
        team_ids: set[int] = set()
        for m in self.db.query(Match).filter(Match.match_date == today_str).all():
            for name in (m.team1_name, m.team2_name):
                tid = self._team_id_by_name(name)
                if tid:
                    team_ids.add(tid)
        if not team_ids:
            return 0

        paid = 0
        day_ref = _date_ref(today)
        for team_id in team_ids:
            row = (
                self.db.query(TeamPowerDaily)
                .filter(TeamPowerDaily.team_id == team_id, TeamPowerDaily.stat_date == today)
                .first()
            )
            progress = row.power_total if row else 0
            contributors = {
                r[0]
                for r in self.db.query(FanActivityLog.user_id)
                .filter(
                    FanActivityLog.team_id == team_id,
                    FanActivityLog.battalion_delta > 0,
                    func.date(FanActivityLog.created_at) == today,
                )
                .distinct()
                .all()
            }
            if not contributors:
                continue
            for tier_idx, goal in enumerate(MATCHDAY_GOALS, start=1):
                if progress < goal:
                    continue
                badge_code = f"matchday_rally_{team_id}_{day_ref}_t{tier_idx}"
                coins = MATCHDAY_REWARDS[tier_idx - 1]
                title = MATCHDAY_TIER_TITLES[tier_idx - 1]
                for uid in contributors:
                    exists = (
                        self.db.query(UserBadge)
                        .filter(UserBadge.user_id == uid, UserBadge.badge_code == badge_code)
                        .first()
                    )
                    if exists:
                        continue
                    user = self.db.query(User).filter(User.id == uid).with_for_update().first()
                    if not user:
                        continue
                    self.wallet.add_coins(user, coins, "matchday_rally_reward", "team", team_id)
                    self.db.add(UserBadge(user_id=uid, badge_code=badge_code, title=title))
                    paid += 1
        if paid:
            self.db.commit()
            cache_delete_prefix("arena:")
        return paid

    def user_has_cheer_extra(self, user_id: int, match_id: int) -> bool:
        return (
            self.db.query(FanActivityLog.id)
            .filter(
                FanActivityLog.user_id == user_id,
                FanActivityLog.activity_type == "boost_cheer_extra",
                FanActivityLog.ref_type == "match",
                FanActivityLog.ref_id == match_id,
            )
            .first()
            is not None
        )

    def _inc_team_power(self, team_id: int, delta: int, user_id: int) -> None:
        today = _utcnow().date()
        row = (
            self.db.query(TeamPowerDaily)
            .filter(TeamPowerDaily.team_id == team_id, TeamPowerDaily.stat_date == today)
            .with_for_update()
            .first()
        )
        if not row:
            row = TeamPowerDaily(team_id=team_id, stat_date=today, power_total=0, active_users=0)
            self.db.add(row)
            self.db.flush()
        row.power_total += delta
        seen_today = (
            self.db.query(FanActivityLog.id)
            .filter(
                FanActivityLog.user_id == user_id,
                FanActivityLog.team_id == team_id,
                func.date(FanActivityLog.created_at) == today,
            )
            .limit(2)
            .count()
        )
        if seen_today <= 1:
            row.active_users += 1

    def _inc_player_heat(self, player_id: int, delta: int, user_id: int, is_boost: bool) -> None:
        today = _utcnow().date()
        row = (
            self.db.query(UserStarHeat)
            .filter(UserStarHeat.user_id == user_id, UserStarHeat.player_id == player_id)
            .with_for_update()
            .first()
        )
        if not row:
            row = UserStarHeat(user_id=user_id, player_id=player_id, heat_total=0)
            self.db.add(row)
            self.db.flush()
        row.heat_total += delta
        daily = (
            self.db.query(PlayerHeatDaily)
            .filter(PlayerHeatDaily.player_id == player_id, PlayerHeatDaily.stat_date == today)
            .with_for_update()
            .first()
        )
        if not daily:
            daily = PlayerHeatDaily(player_id=player_id, stat_date=today, heat_total=0, booster_count=0)
            self.db.add(daily)
            self.db.flush()
        daily.heat_total += delta
        if is_boost:
            daily.booster_count += 1

    def _team_power_in_window(self, team_id: int | None, since: datetime) -> int:
        if not team_id:
            return 0
        total = (
            self.db.query(func.coalesce(func.sum(FanActivityLog.battalion_delta), 0))
            .filter(FanActivityLog.team_id == team_id, FanActivityLog.created_at >= since)
            .scalar()
        )
        return int(total or 0)

    def _can_boost_star(self, user_id: int, player_id: int) -> bool:
        today = _utcnow().date()
        ref_id = _player_date_ref(player_id, today)
        return (
            self.db.query(FanActivityLog)
            .filter(
                FanActivityLog.user_id == user_id,
                FanActivityLog.activity_type == "boost_star",
                FanActivityLog.ref_type == "player_date",
                FanActivityLog.ref_id == ref_id,
            )
            .first()
            is None
        )

    def _fav_players(self, user_id: int) -> list[UserFavoritePlayer]:
        return (
            self.db.query(UserFavoritePlayer)
            .filter(UserFavoritePlayer.user_id == user_id)
            .order_by(UserFavoritePlayer.sort_order)
            .all()
        )

    def _player_has_match_today(self, player_id: int, today: date) -> bool:
        player = self.db.get(PlayerDetailed, player_id)
        if not player:
            return False
        team = self.db.get(Team, player.team_id)
        if not team:
            return False
        today_str = today.isoformat()
        return (
            self.db.query(Match.id)
            .filter(
                or_(Match.team1_name == team.name, Match.team2_name == team.name),
                Match.match_date == today_str,
            )
            .first()
            is not None
        )

    def _team_id_by_name(self, name: str | None) -> int | None:
        if not name:
            return None
        t = self.db.query(Team).filter(Team.name == name).first()
        return t.id if t else None
