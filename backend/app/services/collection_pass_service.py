"""Collection Pass (藏品赛季手册) service."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.collection_pass_catalog import (
    CURRENT_SEASON_CODE,
    DAILY_QUESTS,
    LEVEL_REWARDS,
    LEVEL_THRESHOLDS,
    MAX_LEVEL,
    WEEKLY_QUESTS,
    XP_SOURCES,
    get_season_config,
    level_from_xp,
    xp_to_next_level,
)
from app.db.models.commerce import (
    CollectionPassProgress,
    CollectionPassSeason,
    CollectionPassXpLog,
    CollectionQuestProgress,
    CollectibleEvent,
    User,
    UserBadge,
)
from app.core.cache import cache_get, cache_set
from app.db.repositories.user_repository import WalletRepository

logger = logging.getLogger(__name__)

EVENTS_CACHE_KEY = "collection_pass:active_events_v1"
EVENTS_CACHE_TTL = 60
TRACK_CATALOG_CACHE_KEY = "collection_pass:track_catalog_v1"
TRACK_CATALOG_TTL = 3600


def invalidate_collection_pass_caches() -> None:
    from app.core.cache import cache_delete

    cache_delete(EVENTS_CACHE_KEY)
    cache_delete(TRACK_CATALOG_CACHE_KEY)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CollectionPassService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet = WalletRepository(db)

    def _get_active_season(self) -> CollectionPassSeason:
        now = _utcnow()
        season = (
            self.db.query(CollectionPassSeason)
            .filter(
                CollectionPassSeason.active.is_(True),
                CollectionPassSeason.starts_at <= now,
                CollectionPassSeason.ends_at >= now,
            )
            .order_by(CollectionPassSeason.id.desc())
            .first()
        )
        if not season:
            season = (
                self.db.query(CollectionPassSeason)
                .filter(CollectionPassSeason.code == CURRENT_SEASON_CODE)
                .first()
            )
        if not season:
            cfg = get_season_config()
            start, end = cfg["starts_at"], cfg["ends_at"]
            season = CollectionPassSeason(
                code=CURRENT_SEASON_CODE,
                name=cfg["name"],
                starts_at=datetime.fromisoformat(start.replace("Z", "")),
                ends_at=datetime.fromisoformat(end.replace("Z", "")),
                max_level=MAX_LEVEL,
                config_json=cfg,
                active=True,
            )
            self.db.add(season)
            self.db.flush()
        return season

    def _get_or_create_progress(self, user: User, season: CollectionPassSeason) -> CollectionPassProgress:
        row = (
            self.db.query(CollectionPassProgress)
            .filter(
                CollectionPassProgress.user_id == user.id,
                CollectionPassProgress.season_id == season.id,
            )
            .first()
        )
        if row:
            return row
        row = CollectionPassProgress(
            user_id=user.id,
            season_id=season.id,
            xp=0,
            level=0,
            premium_unlocked=False,
            claimed_free_json=[],
            claimed_premium_json=[],
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _xp_multiplier(self, progress: CollectionPassProgress) -> float:
        if progress.xp_boost_until and progress.xp_boost_until > _utcnow():
            from app.core.config import get_settings

            return get_settings().collection_pass_xp_boost_multiplier
        return 1.0

    def award_xp(
        self,
        user: User,
        source: str,
        ref_type: str,
        ref_id: int,
        amount: int | None = None,
        *,
        commit: bool = False,
    ) -> dict[str, Any]:
        if amount is None:
            amount = XP_SOURCES.get(source, 0)
        if amount <= 0:
            return {"awarded": 0, "reason": "zero_amount"}

        season = self._get_active_season()
        existing = (
            self.db.query(CollectionPassXpLog)
            .filter(
                CollectionPassXpLog.user_id == user.id,
                CollectionPassXpLog.season_id == season.id,
                CollectionPassXpLog.source == source,
                CollectionPassXpLog.ref_type == ref_type,
                CollectionPassXpLog.ref_id == ref_id,
            )
            .first()
        )
        if existing:
            return {"awarded": 0, "reason": "duplicate", "xp": existing.amount}

        progress = self._get_or_create_progress(user, season)
        mult = self._xp_multiplier(progress)
        final_amount = max(1, int(amount * mult)) if mult != 1.0 else amount
        old_level = progress.level or level_from_xp(progress.xp)

        progress.xp += final_amount
        progress.level = level_from_xp(progress.xp)
        self.db.add(
            CollectionPassXpLog(
                user_id=user.id,
                season_id=season.id,
                source=source,
                ref_type=ref_type,
                ref_id=ref_id,
                amount=final_amount,
            )
        )
        self.db.flush()

        leveled_up = progress.level > old_level
        result = {
            "awarded": final_amount,
            "xp": progress.xp,
            "level": progress.level,
            "leveled_up": leveled_up,
            "old_level": old_level,
        }
        if leveled_up:
            try:
                from app.services.notification_service import NotificationService

                NotificationService(self.db).notify_collection_pass_level_up(
                    user.id,
                    progress.level,
                    season.code,
                )
            except Exception:
                pass
        if commit:
            self.db.commit()
        return result

    def bump_quest(self, user: User, action: str, delta: int = 1) -> None:
        today = _utcnow().date()
        daily_key = today.isoformat()
        week_key = today.strftime("%G-W%V")

        for quest in DAILY_QUESTS:
            if quest["action"] != action:
                continue
            self._bump_one_quest(user, quest, daily_key, delta)

        for quest in WEEKLY_QUESTS:
            if quest["action"] != action:
                continue
            self._bump_one_quest(user, quest, week_key, delta)

    def _bump_one_quest(self, user: User, quest: dict, period_key: str, delta: int) -> None:
        row = (
            self.db.query(CollectionQuestProgress)
            .filter(
                CollectionQuestProgress.user_id == user.id,
                CollectionQuestProgress.quest_key == quest["key"],
                CollectionQuestProgress.period_key == period_key,
            )
            .first()
        )
        if not row:
            row = CollectionQuestProgress(
                user_id=user.id,
                quest_key=quest["key"],
                period_key=period_key,
                progress=0,
                target=quest["target"],
            )
            self.db.add(row)
            self.db.flush()
        if row.completed and row.xp_awarded:
            return
        row.progress = min(row.target, row.progress + delta)
        if row.progress >= row.target:
            row.completed = True
            if not row.xp_awarded:
                row.xp_awarded = True
                self.award_xp(
                    user,
                    "quest_daily" if period_key.count("-") == 2 else "quest_weekly",
                    "quest",
                    row.id,
                    amount=quest["xp"],
                )

    def get_track_catalog(self, season: CollectionPassSeason | None = None) -> dict[str, Any]:
        cached = cache_get(TRACK_CATALOG_CACHE_KEY)
        if cached is not None:
            return cached
        season = season or self._get_active_season()
        max_lv = min(season.max_level, MAX_LEVEL)
        tracks = []
        for level in range(1, max_lv + 1):
            rewards = LEVEL_REWARDS.get(level, {"free": {}, "premium": {}})
            tracks.append(
                {
                    "level": level,
                    "threshold_xp": LEVEL_THRESHOLDS[level],
                    "free": rewards.get("free", {}),
                    "premium": rewards.get("premium", {}),
                }
            )
        out = {
            "season_code": season.code,
            "max_level": max_lv,
            "tracks": tracks,
        }
        cache_set(TRACK_CATALOG_CACHE_KEY, out, TRACK_CATALOG_TTL)
        return out

    @staticmethod
    def merge_tracks_with_progress(
        catalog: dict[str, Any],
        progress: CollectionPassProgress,
    ) -> list[dict[str, Any]]:
        claimed_free = set(progress.claimed_free_json or [])
        claimed_premium = set(progress.claimed_premium_json or [])
        user_level = progress.level or 0
        premium = bool(progress.premium_unlocked)
        out: list[dict[str, Any]] = []
        for t in catalog.get("tracks") or []:
            level = int(t["level"])
            out.append(
                {
                    **t,
                    "free_claimed": level in claimed_free,
                    "premium_claimed": level in claimed_premium,
                    "free_claimable": user_level >= level and level not in claimed_free,
                    "premium_claimable": premium and user_level >= level and level not in claimed_premium,
                }
            )
        return out

    @staticmethod
    def _xp_level_progress_pct(xp: int) -> float:
        lv, _ = xp_to_next_level(xp)
        level_start = LEVEL_THRESHOLDS[lv] if lv < MAX_LEVEL else LEVEL_THRESHOLDS[MAX_LEVEL]
        level_end = LEVEL_THRESHOLDS[lv + 1] if lv + 1 <= MAX_LEVEL else LEVEL_THRESHOLDS[MAX_LEVEL]
        span = max(1, level_end - level_start)
        return round(min(100.0, max(0.0, (xp - level_start) / span * 100)), 1)

    def _progress_payload(
        self, user: User, season: CollectionPassSeason, progress: CollectionPassProgress
    ) -> dict[str, Any]:
        lv, xp_need = xp_to_next_level(progress.xp)
        cfg = get_season_config()
        xp_level_progress_pct = self._xp_level_progress_pct(progress.xp)
        return {
            "season": {
                "code": season.code,
                "name": season.name,
                "starts_at": season.starts_at.isoformat() if season.starts_at else None,
                "ends_at": season.ends_at.isoformat() if season.ends_at else None,
                "max_level": season.max_level,
            },
            "xp": progress.xp,
            "level": progress.level,
            "xp_to_next": xp_need,
            "xp_level_progress_pct": xp_level_progress_pct,
            "next_level": lv + 1 if lv < MAX_LEVEL else None,
            "premium_unlocked": progress.premium_unlocked,
            "xp_boost_active": bool(progress.xp_boost_until and progress.xp_boost_until > _utcnow()),
            "xp_boost_until": progress.xp_boost_until.isoformat() if progress.xp_boost_until else None,
            "claimable_count": self._claimable_count(progress, season.max_level),
            "claimed_free_levels": list(progress.claimed_free_json or []),
            "claimed_premium_levels": list(progress.claimed_premium_json or []),
            "compliance_notice": cfg["compliance_notice"],
            "premium_sku": cfg["premium_sku"],
            "premium_price_fen": cfg["premium_price_fen"],
            "premium_plus_sku": cfg.get("premium_plus_sku"),
            "premium_plus_price_fen": cfg.get("premium_plus_price_fen"),
        }

    def get_summary_lite(self, user: User) -> dict[str, Any]:
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        payload = self._progress_payload(user, season, progress)
        payload["quests"] = self._quest_snapshot(user)
        return payload

    def get_summary(self, user: User) -> dict[str, Any]:
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        payload = self._progress_payload(user, season, progress)
        payload["quests"] = self._quest_snapshot(user)
        catalog = self.get_track_catalog(season)
        payload["tracks"] = self.merge_tracks_with_progress(catalog, progress)
        return payload

    def _claimable_count(self, progress: CollectionPassProgress, max_level: int | None = None) -> int:
        cap = min(max_level or MAX_LEVEL, MAX_LEVEL)
        claimed_free = set(progress.claimed_free_json or [])
        claimed_premium = set(progress.claimed_premium_json or [])
        count = 0
        user_level = progress.level or 0
        for level in range(1, cap + 1):
            if user_level < level:
                continue
            if level not in claimed_free:
                count += 1
            if progress.premium_unlocked and level not in claimed_premium:
                count += 1
        return count

    def _quest_snapshot(self, user: User) -> dict[str, list]:
        today = _utcnow().date().isoformat()
        week = _utcnow().date().strftime("%G-W%V")
        quest_keys = [q["key"] for q in DAILY_QUESTS] + [q["key"] for q in WEEKLY_QUESTS]
        rows = (
            self.db.query(CollectionQuestProgress)
            .filter(
                CollectionQuestProgress.user_id == user.id,
                CollectionQuestProgress.quest_key.in_(quest_keys),
                CollectionQuestProgress.period_key.in_({today, week}),
            )
            .all()
        )
        by_key = {(r.quest_key, r.period_key): r for r in rows}
        daily = [self._quest_row_from(quest, today, by_key.get((quest["key"], today))) for quest in DAILY_QUESTS]
        weekly = [self._quest_row_from(quest, week, by_key.get((quest["key"], week))) for quest in WEEKLY_QUESTS]
        return {"daily": daily, "weekly": weekly}

    @staticmethod
    def _quest_row_from(quest: dict, period_key: str, row: CollectionQuestProgress | None) -> dict:
        progress = row.progress if row else 0
        completed = row.completed if row else False
        return {
            "key": quest["key"],
            "title": quest["title"],
            "target": quest["target"],
            "progress": progress,
            "completed": completed,
            "xp": quest["xp"],
        }

    def claim_level_reward(self, user: User, level: int, track: str) -> dict[str, Any]:
        if track not in ("free", "premium"):
            raise BadRequestError("无效轨道")
        if level < 1 or level > MAX_LEVEL:
            raise BadRequestError("无效等级")

        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        progress = (
            self.db.query(CollectionPassProgress)
            .filter(CollectionPassProgress.id == progress.id)
            .with_for_update()
            .one()
        )
        if progress.level < level:
            raise BadRequestError("等级未达成")
        if track == "premium" and not progress.premium_unlocked:
            raise BadRequestError("尚未解锁尊享手册")

        claimed_key = "claimed_free_json" if track == "free" else "claimed_premium_json"
        claimed: list = list(getattr(progress, claimed_key) or [])
        if level in claimed:
            raise BadRequestError("奖励已领取")

        reward = LEVEL_REWARDS.get(level, {}).get(track, {})
        if not reward:
            raise BadRequestError("该等级无奖励")

        grants = self._apply_reward(user, reward, f"collection_pass_{track}", level)
        claimed.append(level)
        setattr(progress, claimed_key, claimed)
        self.db.flush()
        return {"level": level, "track": track, "grants": grants}

    def claim_all_rewards(self, user: User) -> dict[str, Any]:
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        progress = (
            self.db.query(CollectionPassProgress)
            .filter(CollectionPassProgress.id == progress.id)
            .with_for_update()
            .one()
        )
        user_level = progress.level or 0
        if user_level < 1:
            return {"claimed_count": 0, "claims": []}

        claimed_free = list(progress.claimed_free_json or [])
        claimed_premium = list(progress.claimed_premium_json or [])
        claimed_free_set = set(claimed_free)
        claimed_premium_set = set(claimed_premium)
        results: list[dict[str, Any]] = []

        for level in range(1, user_level + 1):
            if level not in claimed_free_set:
                reward = LEVEL_REWARDS.get(level, {}).get("free", {})
                if reward:
                    grants = self._apply_reward(user, reward, "collection_pass_free", level)
                    claimed_free.append(level)
                    claimed_free_set.add(level)
                    results.append({"level": level, "track": "free", "grants": grants})
            if progress.premium_unlocked and level not in claimed_premium_set:
                reward = LEVEL_REWARDS.get(level, {}).get("premium", {})
                if reward:
                    grants = self._apply_reward(user, reward, "collection_pass_premium", level)
                    claimed_premium.append(level)
                    claimed_premium_set.add(level)
                    results.append({"level": level, "track": "premium", "grants": grants})

        progress.claimed_free_json = claimed_free
        progress.claimed_premium_json = claimed_premium
        self.db.flush()
        return {"claimed_count": len(results), "claims": results}

    def _apply_reward(self, user: User, reward: dict, reason: str, ref_id: int) -> dict[str, Any]:
        grants: dict[str, Any] = {}
        if coins := reward.get("fan_coins"):
            self.wallet.add_coins(user, int(coins), reason, "collection_pass", ref_id)
            grants["fan_coins"] = int(coins)
        if redeem := reward.get("redeem_points"):
            self.wallet.add_redeem_points(user, int(redeem), reason, "collection_pass", ref_id)
            grants["redeem_points"] = int(redeem)
        if shards := reward.get("shards"):
            from app.services.collectible_service import CollectibleService

            CollectibleService(self.db).add_shards(user, shards)
            grants["shards"] = shards
        if card_code := reward.get("card_code"):
            from app.services.collectible_service import CollectibleService

            drop = CollectibleService(self.db).drop_cards(
                user,
                "collection_pass",
                "collection_pass_level",
                ref_id,
                card_code=str(card_code),
            )
            grants["collectible_drop"] = drop
        if frame := reward.get("avatar_frame"):
            user.avatar_frame = str(frame)
            grants["avatar_frame"] = str(frame)
        if theme := reward.get("theme_key"):
            user.theme_key = str(theme)
            grants["theme_key"] = str(theme)
        badge_code = reward.get("badge_code")
        badge_title = reward.get("badge_title")
        if badge_code and badge_title:
            if not self.db.query(UserBadge).filter(
                UserBadge.user_id == user.id, UserBadge.badge_code == badge_code
            ).first():
                self.db.add(
                    UserBadge(user_id=user.id, badge_code=str(badge_code), title=str(badge_title))
                )
            grants["badge"] = {"code": badge_code, "title": badge_title}
        return grants

    def unlock_premium(self, user: User) -> dict[str, Any]:
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        progress = (
            self.db.query(CollectionPassProgress)
            .filter(CollectionPassProgress.id == progress.id)
            .with_for_update()
            .one()
        )
        if progress.premium_unlocked:
            return {"already_unlocked": True, "level": progress.level}
        progress.premium_unlocked = True
        badge_code = "collection_pass_premium"
        if not self.db.query(UserBadge).filter(
            UserBadge.user_id == user.id, UserBadge.badge_code == badge_code
        ).first():
            self.db.add(
                UserBadge(user_id=user.id, badge_code=badge_code, title="手册尊享")
            )
        backfill: list[dict[str, Any]] = []
        claimed = list(progress.claimed_premium_json or [])
        for level in range(1, (progress.level or 0) + 1):
            if level in claimed:
                continue
            reward = LEVEL_REWARDS.get(level, {}).get("premium", {})
            if not reward:
                continue
            grants = self._apply_reward(user, reward, "collection_pass_premium", level)
            claimed.append(level)
            backfill.append({"level": level, "grants": grants})
        progress.claimed_premium_json = claimed
        self.db.flush()
        return {
            "premium_unlocked": True,
            "level": progress.level,
            "backfill": backfill,
            "backfill_count": len(backfill),
        }

    def grant_level_skip(self, user: User, levels: int) -> dict[str, Any]:
        from app.core.config import get_settings

        settings = get_settings()
        max_skip = max(1, settings.collection_pass_max_level_skip)
        levels = min(int(levels), max_skip)
        if levels <= 0:
            return {"skipped_levels": 0}
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        progress = (
            self.db.query(CollectionPassProgress)
            .filter(CollectionPassProgress.id == progress.id)
            .with_for_update()
            .one()
        )
        old_level = progress.level or 0
        target_level = min(MAX_LEVEL, old_level + int(levels))
        if target_level <= old_level:
            return {"level": old_level, "skipped_levels": 0}
        progress.xp = max(progress.xp, LEVEL_THRESHOLDS[target_level])
        progress.level = level_from_xp(progress.xp)
        self.db.flush()
        return {
            "level": progress.level,
            "xp": progress.xp,
            "skipped_levels": progress.level - old_level,
        }

    def buy_xp_boost(self, user: User) -> dict[str, Any]:
        from app.core.config import get_settings

        settings = get_settings()
        cost = settings.collection_pass_xp_boost_coin_cost
        hours = settings.collection_pass_xp_boost_hours
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        if (locked.fan_coins or 0) < cost:
            raise BadRequestError(f"球迷币不足，需要 {cost} 币")
        self.wallet.deduct_coins(locked, cost, "collection_pass_xp_boost", "user", locked.id)
        season = self._get_active_season()
        progress = self._get_or_create_progress(locked, season)
        base = progress.xp_boost_until if progress.xp_boost_until and progress.xp_boost_until > _utcnow() else _utcnow()
        progress.xp_boost_until = base + timedelta(hours=hours)
        self.db.flush()
        return {
            "cost": cost,
            "xp_boost_until": progress.xp_boost_until.isoformat(),
            "multiplier": settings.collection_pass_xp_boost_multiplier,
        }

    def pass_nudge(self, user: User) -> dict[str, Any] | None:
        season = self._get_active_season()
        progress = self._get_or_create_progress(user, season)
        lv = progress.level or level_from_xp(progress.xp)
        _, xp_need = xp_to_next_level(progress.xp)
        claimable = self._claimable_count(progress, season.max_level)
        if lv >= MAX_LEVEL and claimable == 0:
            return None
        next_lv = lv + 1 if lv < MAX_LEVEL else lv
        premium_card = None
        if lv < MAX_LEVEL:
            prem = LEVEL_REWARDS.get(next_lv, {}).get("premium", {})
            if prem.get("card_code"):
                premium_card = prem["card_code"]
        body = f"再获得 {xp_need} 经验即可升级" if xp_need else "手册已满级"
        if claimable:
            body = f"{claimable} 项奖励待领取" + (f" · {body}" if xp_need else "")
        elif premium_card and xp_need:
            body += " · 尊享可领限定卡"
        return {
            "level": lv,
            "next_level": next_lv,
            "xp": progress.xp,
            "xp_to_next": xp_need,
            "xp_level_progress_pct": self._xp_level_progress_pct(progress.xp),
            "premium_unlocked": bool(progress.premium_unlocked),
            "next_premium_card": premium_card,
            "claimable_count": claimable,
            "title": f"手册 Lv.{next_lv}" if xp_need else f"手册 Lv.{lv} · 待领取",
            "body": body,
            "path": "/collection?tab=pass",
        }

    @staticmethod
    def hook_award(user: User, db: Session, source: str, ref_type: str, ref_id: int, action: str | None = None) -> None:
        """Non-blocking XP award + quest bump for gameplay hooks."""
        try:
            with db.begin_nested():
                svc = CollectionPassService(db)
                svc.award_xp(user, source, ref_type, ref_id)
                if action:
                    svc.bump_quest(user, action)
        except Exception:
            logger.exception(
                "collection_pass hook_award failed user=%s source=%s ref=%s:%s",
                user.id,
                source,
                ref_type,
                ref_id,
            )

    def get_active_events(self) -> list[CollectibleEvent]:
        now = _utcnow()
        return (
            self.db.query(CollectibleEvent)
            .filter(
                CollectibleEvent.active.is_(True),
                CollectibleEvent.starts_at <= now,
                CollectibleEvent.ends_at >= now,
            )
            .order_by(CollectibleEvent.id.desc())
            .all()
        )

    @staticmethod
    def _event_to_dict(e: CollectibleEvent) -> dict[str, Any]:
        return {
            "code": e.code,
            "name": e.name,
            "description": e.description,
            "starts_at": e.starts_at.isoformat() if e.starts_at else None,
            "ends_at": e.ends_at.isoformat() if e.ends_at else None,
            "event_series": e.event_series,
            "coin_action_cost": e.coin_action_cost,
            "boost_json": e.boost_json or {},
        }

    def event_summary(self) -> list[dict[str, Any]]:
        cached = cache_get(EVENTS_CACHE_KEY)
        if cached is not None:
            return cached
        out = [self._event_to_dict(e) for e in self.get_active_events()]
        cache_set(EVENTS_CACHE_KEY, out, EVENTS_CACHE_TTL)
        return out
