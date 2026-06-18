"""Referral / invite program."""

from __future__ import annotations

import logging
import secrets
import string
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, func, or_, exists, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError
from app.core.rate_limit import rate_limit_referral_register
from app.core.cache import cache_get, cache_set, cache_delete_prefix
from app.db.models.commerce import (
    ReferralBinding,
    ReferralMilestone,
    ReferralSeasonStat,
    ReferralWeeklyAward,
    User,
    UserBadge,
)
from app.db.repositories.user_repository import WalletRepository
from app.services.arena_service import ArenaService

logger = logging.getLogger(__name__)

SEASON_KEY = "wc2026"
_INVITE_ALPHABET = string.ascii_uppercase + string.digits

RECRUITMENT_TIERS = [
    {"count": 1, "title": "初召", "perk": "邀请专属徽章"},
    {"count": 3, "title": "小队", "perk": "召友名片边框"},
    {"count": 5, "title": "扩编", "perk": "永久 +1 免费竞猜/日"},
    {"count": 10, "title": "球探长", "perk": "竞猜积分 +5%（赛季）"},
]

_MILESTONE_NOTIFY_LABELS = {
    "register": "好友注册",
    "profile": "好友完成档案",
    "first_action": "好友首次竞猜/助威",
    "active_7d": "好友 7 日活跃",
    "same_team": "同主队扩编",
}

_MILESTONE_API_KEY = {
    "register": "registered",
    "profile": "profile_done",
    "first_action": "first_action",
    "active_7d": "active_7d",
    "same_team": "same_team",
}

_INVITEE_STEPS = [
    ("register", "完成注册", None, "invitee_coins"),
    ("profile", "完善球迷档案", "/onboarding", "invitee_coins"),
    ("first_action", "首次竞猜或助威", "/predict", "invitee_coins"),
    ("active_7d", "注册后第 7 天签到活跃", None, "inviter_coins"),
    ("same_team", "与邀请人同主队", None, "invitee_battalion"),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _week_key(d: date | None = None) -> str:
    d = d or _utcnow().date()
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-W%W")


def _generate_invite_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))
        exists = db.query(User.id).filter(User.invite_code == code).first()
        if not exists:
            return code
    return secrets.token_hex(4).upper()[:8]


class ReferralService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.wallet = WalletRepository(db)

    def ensure_invite_code(self, user: User) -> str:
        if user.invite_code:
            return user.invite_code
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise BadRequestError("用户不存在")
        if locked.invite_code:
            return locked.invite_code
        locked.invite_code = _generate_invite_code(self.db)
        self.db.commit()
        return locked.invite_code

    def login_referral_info(
        self,
        user: User,
        *,
        is_new: bool,
        invite_code_attempted: str | None,
        bind_failure: str | None = None,
    ) -> dict:
        code = self.ensure_invite_code(user)
        binding = (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.invitee_id == user.id)
            .first()
        )
        inviter_nickname = None
        if binding:
            inviter = self.db.get(User, binding.inviter_id)
            inviter_nickname = inviter.nickname if inviter else None
        bound = binding is not None
        attempted = (invite_code_attempted or "").strip().upper() or None
        message = None
        if is_new and bound and inviter_nickname:
            message = f"{inviter_nickname} 邀请你加入，新手礼包与邀请奖励已到账"
        elif is_new and attempted and not bound:
            failure_messages = {
                "invalid_code": "邀请码无效或不存在，你仍已获得新手球迷币",
                "already_bound": "你已绑定过邀请关系，邀请码无法重复使用",
                "ip_limit": "该邀请今日绑定人数已达上限，请明日再试或联系邀请人",
                "error": "邀请码绑定失败，你仍已获得新手球迷币",
            }
            message = failure_messages.get(
                bind_failure or "",
                "邀请码未生效，你仍已获得新手球迷币",
            )
        return {
            "invite_code": code,
            "is_new": is_new,
            "bound_inviter": bound,
            "bound": bound,
            "inviter_nickname": inviter_nickname,
            "invite_code_attempted": attempted,
            "invite_accepted": bound if attempted else None,
            "bind_failure": bind_failure if attempted and not bound else None,
            "message": message,
        }

    def preview_invite_code(self, code: str) -> dict:
        normalized = (code or "").strip().upper()
        if not normalized or len(normalized) < 4:
            return {"valid": False}
        inviter = self.db.query(User).filter(User.invite_code == normalized).first()
        if not inviter:
            return {"valid": False}
        s = self.settings
        register_bonus = s.referral_register_invitee_coins
        new_user_coins = s.new_user_coins
        return {
            "valid": True,
            "inviter_nickname": inviter.nickname,
            "register_invitee_bonus": register_bonus,
            "total_new_user_coins": new_user_coins + register_bonus,
            "invite_code": normalized,
        }

    def build_invite_link(self, code: str) -> str:
        return f"{self.settings.frontend_base_url.rstrip('/')}/share/invite?ref={code}"

    def bind_on_register(
        self,
        invitee: User,
        invite_code: str | None,
        client_ip: str | None,
        *,
        is_new: bool,
    ) -> str | None:
        """Bind invitee to inviter on registration. Returns failure reason key or None."""
        if not is_new or not invite_code:
            return None
        code = invite_code.strip().upper()
        if not code:
            return None
        inviter = self.db.query(User).filter(User.invite_code == code).first()
        if not inviter or inviter.id == invitee.id:
            return "invalid_code"
        existing = (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.invitee_id == invitee.id)
            .first()
        )
        if existing:
            return "already_bound"
        try:
            rate_limit_referral_register(
                inviter.id, client_ip, limit=self.settings.referral_ip_daily_limit
            )
        except Exception as exc:
            from app.core.exceptions import RateLimitError

            if isinstance(exc, RateLimitError):
                return "ip_limit"
            raise
        binding = ReferralBinding(
            inviter_id=inviter.id,
            invitee_id=invitee.id,
            invite_code_used=code,
            registered_ip=client_ip,
        )
        self.db.add(binding)
        invitee.referred_by_user_id = inviter.id
        self.db.flush()
        invitee.free_cheer_tickets = (invitee.free_cheer_tickets or 0) + 1
        self._grant_milestone(binding, "register", inviter, invitee)
        cache_delete_prefix("referral:weekly:")
        self.db.commit()
        return None

    def on_profile_completed(self, user: User) -> None:
        binding = self._binding_for_invitee(user.id)
        if not binding:
            return
        inviter = self.db.get(User, binding.inviter_id)
        if not inviter:
            return
        self._grant_milestone(binding, "profile", inviter, user)
        if (
            not binding.same_team_bonus_applied
            and user.favorite_team_id
            and inviter.favorite_team_id == user.favorite_team_id
        ):
            binding.same_team_bonus_applied = True
            self._grant_milestone(binding, "same_team", inviter, user)
        self.db.commit()

    def on_first_action(self, user: User) -> None:
        binding = self._binding_for_invitee(user.id)
        if not binding:
            return
        inviter = self.db.get(User, binding.inviter_id)
        if not inviter:
            return
        self._grant_milestone(binding, "first_action", inviter, user)
        self.db.commit()

    def on_signin(self, user: User) -> None:
        binding = self._binding_for_invitee(user.id)
        if not binding:
            return
        if (_utcnow() - (binding.created_at or _utcnow())).days >= 7:
            inviter = self.db.get(User, binding.inviter_id)
            if inviter:
                self._grant_milestone(binding, "active_7d", inviter, user)
                self.db.commit()

    def bonus_free_predictions(self, user_id: int) -> int:
        binding = self._binding_for_invitee(user_id)
        if not binding:
            return 0
        return 1 if binding.status == "active" else 0

    def get_my_stats(self, user: User) -> dict:
        code = self.ensure_invite_code(user)
        invite_link = self.build_invite_link(code)
        bindings = (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.inviter_id == user.id)
            .all()
        )
        total_invites = len(bindings)
        effective_invites = sum(
            1 for b in bindings if self._is_effective_binding(b)
        )
        stat = (
            self.db.query(ReferralSeasonStat)
            .filter(
                ReferralSeasonStat.user_id == user.id,
                ReferralSeasonStat.season_key == SEASON_KEY,
            )
            .first()
        )
        season_coins = stat.coins_earned if stat else 0
        cap = self.settings.referral_max_coins_earned_per_season
        week = _week_key()
        week_board = self.get_weekly_leaderboard(viewer_id=user.id)
        week_score = week_board["my_score"]
        recruitment_tiers = []
        for tier in RECRUITMENT_TIERS:
            recruitment_tiers.append(
                {
                    **tier,
                    "unlocked": effective_invites >= tier["count"],
                }
            )
        next_tier = None
        for tier in RECRUITMENT_TIERS:
            if effective_invites < tier["count"]:
                next_tier = {
                    "count": tier["count"],
                    "title": tier["title"],
                    "remaining": tier["count"] - effective_invites,
                }
                break
        same_team_invites = sum(1 for b in bindings if b.same_team_bonus_applied)
        week_ends = _utcnow().date() - timedelta(days=_utcnow().date().weekday()) + timedelta(days=7)
        settle_at = datetime.combine(week_ends, datetime.min.time())
        seconds_until = max(0, int((settle_at - _utcnow()).total_seconds()))
        return {
            "invite_code": code,
            "invite_link": invite_link,
            "invited_total": total_invites,
            "total_invites": total_invites,
            "effective_invites": effective_invites,
            "coins_earned_season": season_coins,
            "season_coins_earned": season_coins,
            "season_cap_near": season_coins >= int(cap * 0.85),
            "week_score": week_score,
            "week_key": week,
            "weekly_rank": {
                "rank": week_board["my_rank"],
                "score": week_score,
            },
            "next_tier": next_tier,
            "recruitment_tiers": recruitment_tiers,
            "same_team_invites": same_team_invites,
            "invitee_journey": self._build_invitee_journey(user),
            "seconds_until_weekly_settle": seconds_until,
        }

    def list_my_invites(self, user: User) -> list[dict]:
        bindings = (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.inviter_id == user.id)
            .order_by(desc(ReferralBinding.created_at))
            .limit(100)
            .all()
        )
        if not bindings:
            return []
        binding_ids = [b.id for b in bindings]
        invitee_ids = [b.invitee_id for b in bindings]
        invitees = {
            u.id: u
            for u in self.db.query(User).filter(User.id.in_(invitee_ids)).all()
        }
        milestone_rows = (
            self.db.query(ReferralMilestone)
            .filter(ReferralMilestone.binding_id.in_(binding_ids))
            .all()
        )
        by_binding: dict[int, list[ReferralMilestone]] = {}
        for m in milestone_rows:
            by_binding.setdefault(m.binding_id, []).append(m)
        out = []
        for binding in bindings:
            invitee = invitees.get(binding.invitee_id)
            if not invitee:
                continue
            ms = by_binding.get(binding.id, [])
            api_keys = [
                _MILESTONE_API_KEY.get(m.milestone_key, m.milestone_key) for m in ms
            ]
            inviter_coins = sum(m.inviter_coins for m in ms)
            out.append(
                {
                    "invitee_id": invitee.id,
                    "nickname": invitee.nickname,
                    "profile_completed": bool(invitee.profile_completed),
                    "inviter_coins_earned": inviter_coins,
                    "milestones": api_keys,
                    "same_team": binding.same_team_bonus_applied,
                    "next_hint": self._invitee_next_hint(binding, invitee, ms),
                    "nudge_text": self._build_nudge_text(invitee, binding, ms),
                }
            )
        return out

    def get_rules(self) -> dict:
        s = self.settings
        milestone_labels = {
            "registered": "好友注册成功",
            "profile_done": "好友完善球迷档案",
            "first_action": "好友完成首次竞猜或助威",
            "active_7d": "好友注册后第 7 天仍活跃签到",
            "same_team": "好友与你选择相同主队",
        }
        milestones = [
            {
                "key": "registered",
                "label": milestone_labels["registered"],
                "inviter_coins": 0,
                "invitee_coins": s.referral_register_invitee_coins,
                "inviter_battalion": 0,
                "invitee_battalion": 0,
            },
            {
                "key": "profile_done",
                "label": milestone_labels["profile_done"],
                "inviter_coins": s.referral_profile_inviter_coins,
                "invitee_coins": s.referral_profile_invitee_coins,
                "inviter_battalion": 0,
                "invitee_battalion": 0,
            },
            {
                "key": "first_action",
                "label": milestone_labels["first_action"],
                "inviter_coins": s.referral_action_inviter_coins,
                "invitee_coins": s.referral_action_invitee_coins,
                "inviter_battalion": 0,
                "invitee_battalion": 0,
            },
            {
                "key": "active_7d",
                "label": milestone_labels["active_7d"],
                "inviter_coins": s.referral_active_7d_inviter_coins,
                "invitee_coins": 0,
                "inviter_battalion": 0,
                "invitee_battalion": 0,
            },
            {
                "key": "same_team",
                "label": milestone_labels["same_team"],
                "inviter_coins": s.referral_same_team_inviter_coins,
                "invitee_coins": 0,
                "inviter_battalion": s.referral_same_team_battalion,
                "invitee_battalion": s.referral_same_team_invitee_battalion,
            },
        ]
        rank_rewards = [
            {"rank": rank, "points": pts, "coins": coins}
            for rank, (pts, coins) in sorted(s.referral_weekly_rank_rewards_map.items())
        ]
        return {
            "summary": (
                "分享邀请链接，好友注册并完成档案、首玩等里程碑后双方获得球迷币与军团贡献；"
                "成功绑定邀请关系后，被邀人额外获得 1 张助威券。"
                "有效邀请计入扩编档位与召友周榜，每周一结算上周榜发放积分与球迷币。"
                "邀请人本季通过召友获得的球迷币有上限，超出后里程碑不再发币但榜与军团仍累计。"
            ),
            "milestones": milestones,
            "season_coin_cap": s.referral_max_coins_earned_per_season,
            "weekly": {
                "settle_top_n": s.referral_weekly_settle_top_n,
                "rank_rewards": rank_rewards,
            },
        }

    def get_weekly_leaderboard(self, viewer_id: int | None = None) -> dict:
        week_start = _utcnow().date() - timedelta(days=_utcnow().date().weekday())
        cache_key = f"referral:weekly:{week_start.isoformat()}"
        cached = cache_get(cache_key)
        if cached is not None:
            data = dict(cached)
            if viewer_id:
                data["my_rank"] = next(
                    (r["rank"] for r in data["rows"] if r["user_id"] == viewer_id),
                    None,
                )
                data["my_score"] = next(
                    (r["score"] for r in data["rows"] if r["user_id"] == viewer_id),
                    self._weekly_effective_scores(datetime.combine(week_start, datetime.min.time())).get(viewer_id, 0),
                )
            return data
        start_dt = datetime.combine(week_start, datetime.min.time())
        week_ends = week_start + timedelta(days=7)
        settle_at = datetime.combine(week_ends, datetime.min.time())
        seconds_until = max(0, int((settle_at - _utcnow()).total_seconds()))
        scores = self._weekly_effective_scores(start_dt)
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:50]
        user_ids = [uid for uid, _ in sorted_items]
        users = {u.id: u for u in self.db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
        rows = []
        my_rank = None
        my_score = scores.get(viewer_id, 0) if viewer_id else 0
        for idx, (uid, score) in enumerate(sorted_items):
            u = users.get(uid)
            if not u:
                continue
            rank = idx + 1
            if viewer_id == uid:
                my_rank = rank
                my_score = int(score)
            rows.append(
                {
                    "rank": rank,
                    "user_id": uid,
                    "nickname": u.nickname,
                    "score": int(score),
                }
            )
        if viewer_id and my_rank is None:
            my_score = int(scores.get(viewer_id, 0))
        payload = {
            "rows": rows,
            "period_label": f"本周 ({week_start.isoformat()} 起)",
            "my_rank": my_rank,
            "my_score": my_score,
            "seconds_until_settle": seconds_until,
            "week_ends_at": week_ends.isoformat(),
        }
        cache_set(cache_key, {k: v for k, v in payload.items() if k not in ("my_rank", "my_score")}, ttl=60)
        return payload

    def _weekly_effective_scores(
        self,
        start_dt: datetime,
        end_dt: datetime | None = None,
    ) -> dict[int, int]:
        profile_ms = exists(
            select(1).where(
                ReferralMilestone.binding_id == ReferralBinding.id,
                ReferralMilestone.milestone_key == "profile",
            )
        )
        action_ms = exists(
            select(1).where(
                ReferralMilestone.binding_id == ReferralBinding.id,
                ReferralMilestone.milestone_key == "first_action",
            )
        )
        q = (
            self.db.query(
                ReferralBinding.inviter_id,
                func.count(ReferralBinding.id),
            )
            .join(User, User.id == ReferralBinding.invitee_id)
            .filter(
                ReferralBinding.created_at >= start_dt,
                ReferralBinding.status == "active",
                or_(User.profile_completed.is_(True), profile_ms, action_ms),
            )
        )
        if end_dt is not None:
            q = q.filter(ReferralBinding.created_at < end_dt)
        scores: dict[int, int] = {}
        for inviter_id, cnt in q.group_by(ReferralBinding.inviter_id).all():
            scores[int(inviter_id)] = int(cnt)
        return scores

    def settle_previous_week(self) -> dict:
        """Award weekly referral leaderboard (run on Monday for prior week)."""
        today = _utcnow().date()
        if today.weekday() != 0:
            return {"skipped": True, "reason": "not_monday"}
        prev_monday = today - timedelta(days=7)
        prev_sunday = prev_monday + timedelta(days=6)
        week_key = _week_key(prev_monday)
        start_dt = datetime.combine(prev_monday, datetime.min.time())
        end_dt = datetime.combine(prev_sunday + timedelta(days=1), datetime.min.time())
        rewards = self.settings.referral_weekly_rank_rewards_map
        top_n = self.settings.referral_weekly_settle_top_n or 10
        effective_scores = self._weekly_effective_scores(start_dt, end_dt)
        ranked = sorted(effective_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        awarded = 0
        for rank, (uid, score) in enumerate(ranked, start=1):
            if self.db.query(ReferralWeeklyAward).filter(
                ReferralWeeklyAward.user_id == uid,
                ReferralWeeklyAward.week_key == week_key,
            ).first():
                continue
            reward = rewards.get(rank)
            if not reward:
                continue
            points, coins = reward
            user = self.db.query(User).filter(User.id == uid).with_for_update().first()
            if not user:
                continue
            if points > 0:
                self.wallet.add_season_points(user, points, "referral_weekly", "week", rank)
            if coins > 0:
                self._add_referral_coins(user, coins, "referral_weekly")
            try:
                from app.services.notification_service import NotificationService

                parts = []
                if points:
                    parts.append(f"+{points} 累计积分")
                if coins:
                    parts.append(f"+{coins} 球迷币")
                NotificationService(self.db).notify_referral_reward(
                    user.id,
                    title=f"召友周榜第 {rank} 名",
                    body=f"上周召友榜第 {rank} 名，{' · '.join(parts) or '荣誉已记录'}",
                    milestone_key="weekly_rank",
                    binding_id=user.id,
                    coins=coins,
                    points=points,
                    ref_type="referral_week",
                )
            except Exception:
                logger.exception("Weekly referral notify failed user=%s", uid)
            self.db.add(
                ReferralWeeklyAward(
                    user_id=uid,
                    week_key=week_key,
                    rank=rank,
                    score=int(score),
                    points_awarded=points,
                    coins_awarded=coins,
                )
            )
            awarded += 1
        self.db.commit()
        return {"week_key": week_key, "awarded": awarded}

    def _binding_for_invitee(self, invitee_id: int) -> ReferralBinding | None:
        return (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.invitee_id == invitee_id, ReferralBinding.status == "active")
            .first()
        )

    def _is_effective_binding(self, binding: ReferralBinding) -> bool:
        invitee = self.db.get(User, binding.invitee_id)
        if not invitee:
            return False
        if invitee.profile_completed or self._has_milestone(binding.id, "profile"):
            return True
        return self._has_milestone(binding.id, "first_action")

    def _has_milestone(self, binding_id: int, key: str) -> bool:
        return (
            self.db.query(ReferralMilestone.id)
            .filter(
                ReferralMilestone.binding_id == binding_id,
                ReferralMilestone.milestone_key == key,
            )
            .first()
            is not None
        )

    def _invitee_next_hint(
        self,
        binding: ReferralBinding,
        invitee: User,
        milestones: list[ReferralMilestone],
    ) -> str | None:
        keys = {m.milestone_key for m in milestones}
        if "profile" not in keys and not invitee.profile_completed:
            return "等待好友完善档案"
        if "first_action" not in keys:
            return "等待好友首次竞猜或助威"
        if "active_7d" not in keys:
            days = (_utcnow() - (binding.created_at or _utcnow())).days
            if days < 7:
                return f"好友需在注册后 7 日内活跃（剩余约 {7 - days} 天）"
        return None

    def _build_invitee_journey(self, user: User) -> dict | None:
        binding = self._binding_for_invitee(user.id)
        if not binding:
            return None
        inviter = self.db.get(User, binding.inviter_id)
        milestones = (
            self.db.query(ReferralMilestone)
            .filter(ReferralMilestone.binding_id == binding.id)
            .all()
        )
        done_keys = {m.milestone_key for m in milestones}
        steps = []
        next_step = None
        for key, label, action, reward_field in _INVITEE_STEPS:
            cfg = self._milestone_config(key)
            reward_coins = None
            reward_battalion = None
            if cfg:
                if reward_field == "invitee_coins":
                    reward_coins = cfg["invitee"][0] or None
                elif reward_field == "inviter_coins":
                    reward_coins = cfg["inviter"][0] or None
                elif reward_field == "invitee_battalion":
                    reward_battalion = cfg["invitee"][1] or None
            done = key in done_keys or (
                key == "profile" and user.profile_completed
            )
            step = {
                "key": _MILESTONE_API_KEY.get(key, key),
                "label": label,
                "done": done,
            }
            if reward_coins:
                step["reward_coins"] = reward_coins
            if reward_battalion:
                step["reward_battalion"] = reward_battalion
            if action:
                step["action"] = action
            steps.append(step)
            if not done and next_step is None:
                next_step = {
                    "key": _MILESTONE_API_KEY.get(key, key),
                    "label": label,
                }
                if action:
                    next_step["action"] = action
        days_left = None
        if "active_7d" not in done_keys and binding.created_at:
            elapsed = (_utcnow() - binding.created_at).days
            days_left = max(0, 7 - elapsed)
        return {
            "inviter_nickname": inviter.nickname if inviter else "好友",
            "steps": steps,
            "next_step": next_step,
            "days_left_active": days_left,
        }

    def _grant_milestone(
        self,
        binding: ReferralBinding,
        key: str,
        inviter: User,
        invitee: User,
    ) -> None:
        exists = (
            self.db.query(ReferralMilestone)
            .filter(
                ReferralMilestone.binding_id == binding.id,
                ReferralMilestone.milestone_key == key,
            )
            .first()
        )
        if exists:
            return
        cfg = self._milestone_config(key)
        if not cfg:
            return
        inv_coins, inv_battalion, inv_points = cfg["inviter"]
        inv_coins = self._cap_inviter_coins(inviter.id, inv_coins)
        if inv_coins > 0:
            self._add_referral_coins(inviter, inv_coins, f"referral_{key}")
        if inv_points > 0:
            self.wallet.add_season_points(inviter, inv_points, f"referral_{key}", "binding", binding.id)
        if inv_battalion > 0:
            ArenaService(self.db).record_activity(
                inviter,
                f"referral_{key}",
                team_id=inviter.favorite_team_id,
                battalion_delta=inv_battalion,
                ref_type="referral_binding",
                ref_id=binding.id,
            )
        inv_coins_i, inv_battalion_i, _ = cfg["invitee"]
        if inv_coins_i > 0:
            self.wallet.add_coins(invitee, inv_coins_i, f"referral_{key}_invitee", "binding", binding.id)
        if inv_battalion_i > 0:
            ArenaService(self.db).record_activity(
                invitee,
                f"referral_{key}_invitee",
                team_id=invitee.favorite_team_id,
                battalion_delta=inv_battalion_i,
                ref_type="referral_binding",
                ref_id=binding.id,
            )
        self.db.add(
            ReferralMilestone(
                binding_id=binding.id,
                milestone_key=key,
                inviter_coins=inv_coins,
                invitee_coins=inv_coins_i,
                inviter_battalion=inv_battalion,
                invitee_battalion=inv_battalion_i,
                inviter_points=inv_points,
            )
        )
        self._notify_milestone_rewards(
            binding, key, inviter, invitee, inv_coins, inv_battalion, inv_points, inv_coins_i, inv_battalion_i
        )
        try:
            from app.services.collectible_service import CollectibleService

            CollectibleService(self.db).referral_milestone_drop(invitee, key, binding.id)
            if key in ("profile", "first_action"):
                CollectibleService(self.db).referral_inviter_drop(inviter, key, binding.id)
        except Exception:
            logger.exception("Collectible referral drop failed binding=%s key=%s", binding.id, key)
        if key in ("profile", "first_action"):
            self._sync_recruitment_tiers(inviter)
        cache_delete_prefix("referral:weekly:")

    def _notify_milestone_rewards(
        self,
        binding: ReferralBinding,
        key: str,
        inviter: User,
        invitee: User,
        inv_coins: int,
        inv_battalion: int,
        inv_points: int,
        inv_coins_i: int,
        inv_battalion_i: int,
    ) -> None:
        from app.services.notification_service import NotificationService

        label = _MILESTONE_NOTIFY_LABELS.get(key, key)
        notifier = NotificationService(self.db)
        inviter_action = "/invite"
        invitee_action = {
            "profile": "/onboarding",
            "first_action": "/predict",
            "register": "/onboarding?from=referral",
        }.get(key, "/me")
        if inv_coins > 0 or inv_battalion > 0 or inv_points > 0:
            parts: list[str] = []
            if inv_coins:
                parts.append(f"+{inv_coins} 球迷币")
            if inv_points:
                parts.append(f"+{inv_points} 累计积分")
            if inv_battalion:
                parts.append(f"+{inv_battalion} 军团贡献")
            notifier.notify_referral_reward(
                inviter.id,
                title=f"召友奖励 · {label}",
                body=f"好友 {invitee.nickname} {label}，{' · '.join(parts)}",
                milestone_key=key,
                binding_id=binding.id,
                coins=inv_coins,
                battalion=inv_battalion,
                points=inv_points,
                action=inviter_action,
            )
        if inv_coins_i > 0 or inv_battalion_i > 0:
            parts_i: list[str] = []
            if inv_coins_i:
                parts_i.append(f"+{inv_coins_i} 球迷币")
            if inv_battalion_i:
                parts_i.append(f"+{inv_battalion_i} 军团贡献")
            notifier.notify_referral_reward(
                invitee.id,
                title=f"邀请奖励 · {label}",
                body=f"你完成了「{label}」，{' · '.join(parts_i)}",
                milestone_key=f"{key}_invitee",
                binding_id=binding.id,
                coins=inv_coins_i,
                battalion=inv_battalion_i,
                action=invitee_action,
            )

    def _milestone_config(self, key: str) -> dict | None:
        s = self.settings
        table = {
            "register": {
                "inviter": (0, 0, 0),
                "invitee": (s.referral_register_invitee_coins, 0, 0),
            },
            "profile": {
                "inviter": (s.referral_profile_inviter_coins, 0, 0),
                "invitee": (s.referral_profile_invitee_coins, 0, 0),
            },
            "first_action": {
                "inviter": (s.referral_action_inviter_coins, 0, 0),
                "invitee": (s.referral_action_invitee_coins, 0, 0),
            },
            "active_7d": {
                "inviter": (s.referral_active_7d_inviter_coins, 0, 0),
                "invitee": (0, 0, 0),
            },
            "same_team": {
                "inviter": (s.referral_same_team_inviter_coins, s.referral_same_team_battalion, 0),
                "invitee": (0, s.referral_same_team_invitee_battalion, 0),
            },
        }
        return table.get(key)

    def _build_nudge_text(
        self,
        invitee: User,
        binding: ReferralBinding,
        milestones: list[ReferralMilestone],
    ) -> str | None:
        keys = {m.milestone_key for m in milestones}
        if "profile" not in keys and not invitee.profile_completed:
            return f"嗨 {invitee.nickname}，来「最后一舞」完善球迷档案，双方都能领币！"
        if "first_action" not in keys:
            return f"嗨 {invitee.nickname}，来猜一场世界杯吧，完成首玩还能解锁邀请奖励～"
        if "active_7d" not in keys:
            days = (_utcnow() - (binding.created_at or _utcnow())).days
            if days < 7:
                return f"嗨 {invitee.nickname}，记得每天签到，注册后第 7 天活跃还能帮我拿奖励！"
        return None

    def _sync_recruitment_tiers(self, inviter: User) -> None:
        locked = self.db.query(User).filter(User.id == inviter.id).with_for_update().first()
        if not locked:
            return
        inviter = locked
        bindings = (
            self.db.query(ReferralBinding)
            .filter(ReferralBinding.inviter_id == inviter.id)
            .all()
        )
        effective = sum(1 for b in bindings if self._is_effective_binding(b))
        granted = inviter.referral_tier_granted or 0
        if effective >= 1 and granted < 1:
            self._award_referral_badge(inviter, "referral_host", "初召球探")
            inviter.referral_tier_granted = 1
        if effective >= 3 and granted < 3:
            if not inviter.avatar_frame:
                inviter.avatar_frame = "referral_squad"
            inviter.referral_tier_granted = 3
        if effective >= 5 and granted < 5:
            inviter.extra_free_predict_daily = (inviter.extra_free_predict_daily or 0) + 1
            inviter.referral_tier_granted = 5
            try:
                from app.services.notification_service import NotificationService

                NotificationService(self.db).notify_referral_reward(
                    inviter.id,
                    title="召友扩编解锁",
                    body="有效邀请达 5 人，永久 +1 每日免费竞猜",
                    milestone_key="tier_5",
                    binding_id=inviter.id,
                    coins=0,
                )
            except Exception:
                logger.exception("Tier 5 notify failed")
        if effective >= 10 and granted < 10:
            self._award_referral_badge(inviter, "referral_elite", "球探长")
            inviter.referral_tier_granted = 10
            try:
                from app.services.notification_service import NotificationService

                NotificationService(self.db).notify_referral_reward(
                    inviter.id,
                    title="召友球探长解锁",
                    body="有效邀请达 10 人，本赛季竞猜积分 +5%",
                    milestone_key="tier_10",
                    binding_id=inviter.id,
                )
            except Exception:
                logger.exception("Tier 10 notify failed")

    def _award_referral_badge(self, user: User, code: str, title: str) -> None:
        exists = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == user.id, UserBadge.badge_code == code)
            .first()
        )
        if not exists:
            self.db.add(UserBadge(user_id=user.id, badge_code=code, title=title))

    def _cap_inviter_coins(self, user_id: int, amount: int) -> int:
        if amount <= 0:
            return 0
        stat = (
            self.db.query(ReferralSeasonStat)
            .filter(
                ReferralSeasonStat.user_id == user_id,
                ReferralSeasonStat.season_key == SEASON_KEY,
            )
            .with_for_update()
            .first()
        )
        if not stat:
            stat = ReferralSeasonStat(user_id=user_id, season_key=SEASON_KEY, coins_earned=0)
            self.db.add(stat)
            self.db.flush()
        cap = self.settings.referral_max_coins_earned_per_season
        room = max(0, cap - (stat.coins_earned or 0))
        grant = min(amount, room)
        if grant > 0:
            stat.coins_earned = (stat.coins_earned or 0) + grant
        return grant

    def _add_referral_coins(self, user: User, amount: int, reason: str) -> None:
        if amount <= 0:
            return
        self.wallet.add_coins(user, amount, reason, "user", user.id)
