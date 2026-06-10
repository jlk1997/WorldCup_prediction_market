"""Leaderboards: season points, redeem points, predict accuracy."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.db.models.commerce import GamePrediction, PointLedger, User
from app.services.arena_service import TIER_LABELS

PERIOD_LABELS = {
    "daily": "今日",
    "weekly": "本周",
    "season": "赛季总榜",
}

BOARD_RULES = {
    "points": {
        "daily": "今日累计积分增量（猜中、召友荣誉等）",
        "weekly": "本周累计积分增量",
        "season": "赛季累计积分总榜（兑换不扣减）",
    },
    "redeem_points": {
        "daily": "今日可用积分增量（仅竞猜猜中）",
        "weekly": "本周可用积分增量",
        "season": "可用积分余额榜（用于积分兑换商城）",
    },
    "battalion": {
        "daily": "今日军团贡献",
        "weekly": "本周军团贡献",
        "season": "赛季军团贡献总榜",
    },
    "predict_accuracy": {
        "season": "至少 5 场已结算竞猜，按猜中率排序",
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _period_start(period: str) -> datetime | None:
    today = _utcnow().date()
    if period == "daily":
        return datetime.combine(today, datetime.min.time())
    if period == "weekly":
        monday = today - timedelta(days=today.weekday())
        return datetime.combine(monday, datetime.min.time())
    return None


class LeaderboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_rules(self) -> dict:
        return {"boards": BOARD_RULES, "periods": PERIOD_LABELS}

    def legacy_points_list(self, period: str, limit: int = 50) -> list[dict]:
        data = self.get_points_board(period, limit, viewer_id=None)
        return [
            {
                "user_id": r["user_id"],
                "nickname": r["nickname"],
                "season_points": r["points"],
                "points": r["points"],
                "win_streak": r.get("win_streak", 0),
            }
            for r in data["rows"]
        ]

    def get_points_board(self, period: str, limit: int, viewer_id: int | None = None) -> dict:
        p = period if period in PERIOD_LABELS else "season"
        if p == "season":
            rows = self._balance_board("season", limit, viewer_id)
            metric = "season_points"
        else:
            rows = self._delta_board("season", p, limit, viewer_id)
            metric = "season_points_delta"
        return {
            "board": "points",
            "period": p,
            "period_label": PERIOD_LABELS[p],
            "metric": metric,
            "description": BOARD_RULES["points"][p],
            "rows": rows,
        }

    def get_redeem_points_board(self, period: str, limit: int, viewer_id: int | None = None) -> dict:
        p = period if period in PERIOD_LABELS else "season"
        if p == "season":
            rows = self._balance_board("redeem", limit, viewer_id)
            metric = "redeem_points"
        else:
            rows = self._delta_board("redeem", p, limit, viewer_id)
            metric = "redeem_points_delta"
        return {
            "board": "redeem_points",
            "period": p,
            "period_label": PERIOD_LABELS[p],
            "metric": metric,
            "description": BOARD_RULES["redeem_points"][p],
            "rows": rows,
        }

    def get_predict_accuracy_board(
        self, limit: int = 50, viewer_id: int | None = None, min_samples: int = 5
    ) -> dict:
        subq = (
            self.db.query(
                GamePrediction.user_id.label("uid"),
                func.count(GamePrediction.id).label("settled"),
                func.sum(case((GamePrediction.status == "won", 1), else_=0)).label("wins"),
            )
            .filter(GamePrediction.status.in_(("won", "lost")))
            .group_by(GamePrediction.user_id)
            .subquery()
        )
        q = (
            self.db.query(User, subq.c.settled, subq.c.wins)
            .join(subq, User.id == subq.c.uid)
            .filter(subq.c.settled >= min_samples)
        )
        rows_raw = q.all()
        scored: list[tuple[User, int, int, float]] = []
        for user, settled, wins in rows_raw:
            settled_i = int(settled or 0)
            wins_i = int(wins or 0)
            rate = round(wins_i / settled_i * 100, 1) if settled_i else 0.0
            scored.append((user, settled_i, wins_i, rate))
        scored.sort(key=lambda x: (-x[3], -x[2], x[0].id))
        rows = []
        for idx, (user, settled_i, wins_i, rate) in enumerate(scored[:limit]):
            rows.append(
                {
                    "rank": idx + 1,
                    "user_id": user.id,
                    "nickname": user.nickname,
                    "win_rate": rate,
                    "wins": wins_i,
                    "settled": settled_i,
                    "points": rate,
                    "win_streak": user.win_streak or 0,
                    "arena_tier": user.arena_tier,
                    "tier_label": TIER_LABELS.get(user.arena_tier or "rookie"),
                    "is_me": viewer_id is not None and user.id == viewer_id,
                }
            )
        return {
            "board": "predict_accuracy",
            "period": "season",
            "period_label": "赛季",
            "metric": "win_rate",
            "description": BOARD_RULES["predict_accuracy"]["season"],
            "min_samples": min_samples,
            "rows": rows,
        }

    def get_my_summary(self, user: User) -> dict:
        season_rank = self._season_points_rank(user)
        redeem_rank = self._balance_rank(user.id, "redeem")
        daily_pts = self._user_delta(user.id, "season", "daily")
        weekly_pts = self._user_delta(user.id, "season", "weekly")
        redeem_daily = self._user_delta(user.id, "redeem", "daily")
        redeem_weekly = self._user_delta(user.id, "redeem", "weekly")
        daily_rank = self._delta_rank(user.id, "season", "daily") if daily_pts else None
        weekly_rank = self._delta_rank(user.id, "season", "weekly") if weekly_pts else None
        redeem_daily_rank = self._delta_rank(user.id, "redeem", "daily") if redeem_daily else None
        redeem_weekly_rank = self._delta_rank(user.id, "redeem", "weekly") if redeem_weekly else None
        battalion_rank = None
        battalion_team = None
        if user.favorite_team_id:
            from app.services.arena_service import ArenaService

            standing = ArenaService(self.db).get_my_standing(user)
            battalion_rank = standing.get("rank")
            battalion_team = (standing.get("team") or {}).get("name")
        preds = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.user_id == user.id, GamePrediction.status.in_(("won", "lost")))
            .all()
        )
        settled = len(preds)
        wins = sum(1 for p in preds if p.status == "won")
        win_rate = round(wins / settled * 100, 1) if settled else 0.0
        acc_rank = None
        if settled >= 5:
            board = self.get_predict_accuracy_board(limit=200, viewer_id=user.id)
            for row in board["rows"]:
                if row["user_id"] == user.id:
                    acc_rank = row["rank"]
                    break
        return {
            "user_id": user.id,
            "nickname": user.nickname,
            "season_points": user.season_points or 0,
            "season_rank": season_rank,
            "season_gap_to_prev": self._gap_to_prev(user, "season"),
            "redeem_points": user.redeem_points or 0,
            "redeem_rank": redeem_rank,
            "redeem_gap_to_prev": self._gap_to_prev(user, "redeem"),
            "daily_points": daily_pts,
            "daily_rank": daily_rank,
            "redeem_daily_points": redeem_daily,
            "redeem_daily_rank": redeem_daily_rank,
            "weekly_points": weekly_pts,
            "weekly_rank": weekly_rank,
            "redeem_weekly_points": redeem_weekly,
            "redeem_weekly_rank": redeem_weekly_rank,
            "win_streak": user.win_streak or 0,
            "battalion_points": user.battalion_points_season or 0,
            "battalion_rank": battalion_rank,
            "battalion_team": battalion_team,
            "arena_tier": user.arena_tier or "rookie",
            "tier_label": TIER_LABELS.get(user.arena_tier or "rookie", "新兵"),
            "predict": {
                "settled": settled,
                "wins": wins,
                "win_rate": win_rate,
            },
            "predict_accuracy_rank": acc_rank,
        }

    def _season_points_rank(self, user: User) -> int | None:
        higher = (
            self.db.query(User)
            .filter(User.season_points > (user.season_points or 0))
            .count()
        )
        return higher + 1 if (user.season_points or 0) > 0 or True else None

    def _gap_to_prev(self, user: User, bucket: str = "season") -> int | None:
        col = User.season_points if bucket == "season" else User.redeem_points
        my_pts = user.season_points if bucket == "season" else (user.redeem_points or 0)
        if my_pts <= 0:
            return None
        prev = (
            self.db.query(User)
            .filter(col > my_pts)
            .order_by(col.asc(), User.id.asc())
            .first()
        )
        if not prev:
            return None
        prev_pts = prev.season_points if bucket == "season" else (prev.redeem_points or 0)
        return max(1, prev_pts - my_pts + 1)

    def _balance_board(self, bucket: str, limit: int, viewer_id: int | None) -> list[dict]:
        col = User.season_points if bucket == "season" else User.redeem_points
        users = (
            self.db.query(User)
            .filter(col > 0)
            .order_by(desc(col), User.id)
            .limit(limit)
            .all()
        )
        rows = []
        for idx, u in enumerate(users):
            pts = u.season_points if bucket == "season" else (u.redeem_points or 0)
            rows.append(
                {
                    "rank": idx + 1,
                    "user_id": u.id,
                    "nickname": u.nickname,
                    "points": pts,
                    "season_points": u.season_points if bucket == "season" else None,
                    "redeem_points": u.redeem_points if bucket == "redeem" else None,
                    "win_streak": u.win_streak or 0,
                    "arena_tier": u.arena_tier,
                    "tier_label": TIER_LABELS.get(u.arena_tier or "rookie"),
                    "is_me": viewer_id is not None and u.id == viewer_id,
                }
            )
        return rows

    def _delta_board(self, bucket: str, period: str, limit: int, viewer_id: int | None) -> list[dict]:
        start = _period_start(period)
        if not start:
            return self._balance_board(bucket, limit, viewer_id)
        q = (
            self.db.query(
                PointLedger.user_id,
                func.sum(PointLedger.delta).label("pts"),
            )
            .filter(
                PointLedger.point_bucket == bucket,
                PointLedger.delta > 0,
                PointLedger.created_at >= start,
            )
            .group_by(PointLedger.user_id)
            .order_by(desc("pts"))
            .limit(limit)
        )
        agg = q.all()
        user_ids = [uid for uid, _ in agg]
        users_map = {u.id: u for u in self.db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
        rows = []
        for idx, (uid, pts) in enumerate(agg):
            u = users_map.get(uid)
            if not u:
                continue
            rows.append(
                {
                    "rank": idx + 1,
                    "user_id": uid,
                    "nickname": u.nickname,
                    "points": int(pts or 0),
                    "win_streak": u.win_streak or 0,
                    "arena_tier": u.arena_tier,
                    "tier_label": TIER_LABELS.get(u.arena_tier or "rookie"),
                    "is_me": viewer_id is not None and uid == viewer_id,
                }
            )
        if viewer_id and not any(r["user_id"] == viewer_id for r in rows):
            my_pts = self._user_delta(viewer_id, bucket, period)
            if my_pts > 0:
                u = self.db.get(User, viewer_id)
                if u:
                    rows.append(
                        {
                            "rank": self._delta_rank(viewer_id, bucket, period) or len(rows) + 1,
                            "user_id": viewer_id,
                            "nickname": u.nickname,
                            "points": my_pts,
                            "win_streak": u.win_streak or 0,
                            "arena_tier": u.arena_tier,
                            "tier_label": TIER_LABELS.get(u.arena_tier or "rookie"),
                            "is_me": True,
                        }
                    )
        return rows

    def _balance_rank(self, user_id: int, bucket: str) -> int | None:
        user = self.db.get(User, user_id)
        if not user:
            return None
        col_val = user.season_points if bucket == "season" else (user.redeem_points or 0)
        higher = (
            self.db.query(User)
            .filter(
                (User.season_points if bucket == "season" else User.redeem_points) > col_val
            )
            .count()
        )
        return higher + 1

    def _user_delta(self, user_id: int, bucket: str, period: str) -> int:
        start = _period_start(period)
        if not start:
            return 0
        val = (
            self.db.query(func.coalesce(func.sum(PointLedger.delta), 0))
            .filter(
                PointLedger.user_id == user_id,
                PointLedger.point_bucket == bucket,
                PointLedger.delta > 0,
                PointLedger.created_at >= start,
            )
            .scalar()
        )
        return int(val or 0)

    def _delta_rank(self, user_id: int, bucket: str, period: str) -> int | None:
        start = _period_start(period)
        if not start:
            return None
        my_pts = self._user_delta(user_id, bucket, period)
        if my_pts <= 0:
            return None
        subq = (
            self.db.query(
                PointLedger.user_id,
                func.sum(PointLedger.delta).label("pts"),
            )
            .filter(
                PointLedger.point_bucket == bucket,
                PointLedger.delta > 0,
                PointLedger.created_at >= start,
            )
            .group_by(PointLedger.user_id)
            .subquery()
        )
        higher = self.db.query(subq).filter(subq.c.pts > my_pts).count()
        return higher + 1
