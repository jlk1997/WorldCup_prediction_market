"""Collectible card / digital collectibles service (compliance-first, no trading)."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.collectible_catalog import (
    DROP_WEIGHTS_BY_SOURCE,
    SHARD_ON_DUPLICATE,
    SYNTHESIS_COST,
    UPGRADE_STAR_COST,
)
from app.db.models import Match, PlayerDetailed, Team
from app.db.models.commerce import (
    CardSetDefinition,
    CardSetProgress,
    CollectibleCard,
    CollectibleDropLog,
    CollectibleShard,
    User,
    UserBadge,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository

logger = logging.getLogger(__name__)

RARITY_ORDER = ("common", "rare", "epic", "legend")
MAX_STAR = 3

COMPLIANCE_NOTICE = (
    "球星卡为平台内虚拟数字藏品，以可用积分（站内虚拟积分，无现金价值、不可提现）进行收藏与流通。"
    "行情仅供收藏体验参考，不构成任何投资建议。"
)

# Catalog metadata cache (invalidated on sync_collectible_catalog)
_catalog_cache: dict[str, Any] = {"series_options": None, "total_active": None}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def invalidate_collectible_catalog_cache() -> None:
    _catalog_cache["series_options"] = None
    _catalog_cache["total_active"] = None


class CollectibleService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet = WalletRepository(db)
        self._event_boost_cached: dict | None = None

    def drop_cards(
        self,
        user: User,
        source: str,
        ref_type: str,
        ref_id: int,
        *,
        match_id: int | None = None,
        force_rarity: str | None = None,
        team_boost_id: int | None = None,
        card_code: str | None = None,
    ) -> dict[str, Any]:
        """Idempotent card drop. Returns drop result for UI/WS payload."""
        existing = (
            self.db.query(CollectibleDropLog)
            .filter(
                CollectibleDropLog.user_id == user.id,
                CollectibleDropLog.source == source,
                CollectibleDropLog.ref_type == ref_type,
                CollectibleDropLog.ref_id == ref_id,
            )
            .first()
        )
        if existing and existing.result_json:
            return existing.result_json

        boost_team = team_boost_id or user.favorite_team_id
        match_team_ids = self._match_team_ids(match_id) if match_id else set()

        drops: list[dict] = []
        shard_grants: list[dict] = []

        rarity = force_rarity or self._roll_rarity(source)
        if card_code:
            card = self.db.query(CollectibleCard).filter(CollectibleCard.code == card_code, CollectibleCard.active.is_(True)).first()
        else:
            card = self._pick_card(rarity, boost_team, match_team_ids, source)
        if not card:
            card = self._pick_card("common", boost_team, match_team_ids, source)
        if not card:
            result = {"dropped": False, "cards": [], "shards": [], "source": source, "chain_enabled": self._chain_enabled()}
            self._save_drop_log(user.id, source, ref_type, ref_id, result)
            return result

        grant = self._grant_card(user, card, source)
        if grant["is_duplicate"]:
            shard_amount = SHARD_ON_DUPLICATE.get(card.rarity, 5)
            self._add_shards(user.id, card.rarity, shard_amount)
            shard_grants.append({"rarity": card.rarity, "amount": shard_amount, "reason": "duplicate"})
            drops.append({**self._card_brief(card, grant), "is_duplicate": True, "shards_gained": shard_amount})
        else:
            drops.append({**self._card_brief(card, grant), "is_duplicate": False})

        result = {
            "dropped": True,
            "cards": drops,
            "shards": shard_grants,
            "source": source,
            "chain_enabled": self._chain_enabled(),
        }
        log_id = self._save_drop_log(user.id, source, ref_type, ref_id, result)
        self._notify_drop(user, result, log_id)
        if result.get("dropped"):
            from app.services.collection_pass_service import CollectionPassService

            CollectionPassService.hook_award(
                user, self.db, "card_drop", ref_type, ref_id or 0, action=None
            )
        return result

    def signin_drop_if_milestone(self, user: User, streak: int) -> dict[str, Any] | None:
        if streak not in (3, 7, 14):
            return None
        rarity_map = {3: "rare", 7: "epic", 14: "legend"}
        return self.drop_cards(
            user,
            "signin",
            "signin_streak",
            streak,
            force_rarity=rarity_map[streak],
            team_boost_id=user.favorite_team_id,
        )

    def referral_milestone_drop(self, user: User, milestone_key: str, binding_id: int) -> dict[str, Any] | None:
        if milestone_key not in ("first_action", "profile"):
            return None
        rarity = "epic" if milestone_key == "first_action" else "rare"
        return self.drop_cards(
            user,
            "referral",
            "referral_binding",
            binding_id,
            force_rarity=rarity,
            team_boost_id=user.favorite_team_id,
        )

    def referral_inviter_drop(self, user: User, milestone_key: str, binding_id: int) -> dict[str, Any] | None:
        if milestone_key not in ("first_action", "profile"):
            return None
        rarity = "rare" if milestone_key == "first_action" else "common"
        return self.drop_cards(
            user,
            "referral",
            "referral_inviter",
            binding_id,
            force_rarity=rarity,
            team_boost_id=user.favorite_team_id,
        )

    def matchday_drop(self, user: User, team_id: int) -> dict[str, Any]:
        limited_code = f"matchday_{team_id}"
        limited = (
            self.db.query(CollectibleCard)
            .filter(CollectibleCard.code == limited_code, CollectibleCard.active.is_(True))
            .first()
        )
        if limited and random.random() < 0.42:
            return self.drop_cards(
                user,
                "matchday",
                "team",
                team_id,
                team_boost_id=team_id,
                card_code=limited_code,
            )
        return self.drop_cards(
            user,
            "matchday",
            "team",
            team_id,
            team_boost_id=team_id,
        )

    def add_shards(self, user: User, shards: dict[str, int]) -> None:
        for rarity, amount in shards.items():
            if amount and int(amount) > 0:
                self._add_shards(user.id, str(rarity), int(amount))

    def synthesize(self, user: User, card_code: str, *, use_coin_fill: bool = False) -> dict[str, Any]:
        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == card_code, CollectibleCard.active.is_(True)).first()
        if not card:
            raise NotFoundError("卡牌不存在")
        if card.rarity == "legend":
            raise BadRequestError("传奇卡不可合成")
        cost = SYNTHESIS_COST.get(card.rarity)
        if not cost:
            raise BadRequestError("该稀有度不可合成")

        owned = self._user_owns_card(user.id, card.id)
        if owned:
            raise BadRequestError("你已拥有该卡牌")

        shard_row = self._get_shard_row(user.id, card.rarity, for_update=True)
        coins_spent = 0
        shard_need = cost["shards"]
        shard_have = shard_row.amount or 0
        if shard_have < shard_need:
            deficit = shard_need - shard_have
            if not use_coin_fill:
                raise BadRequestError(f"碎片不足，需要 {shard_need} 个{card.rarity}碎片")
            coins_spent = self._buy_shards_with_coins(user, card.rarity, deficit)
            shard_row = self._get_shard_row(user.id, card.rarity, for_update=True)
        if (shard_row.amount or 0) < shard_need:
            raise BadRequestError(f"碎片不足，需要 {shard_need} 个{card.rarity}碎片")
        if (user.redeem_points or 0) < cost["redeem_points"]:
            raise BadRequestError(f"可用积分不足，需要 {cost['redeem_points']} 分")

        shard_row.amount -= cost["shards"]
        self.wallet.deduct_redeem_points(
            user, cost["redeem_points"], "collectible_synthesize", "collectible_card", card.id
        )
        grant = self._grant_card(user, card, "synthesis", increment=False)
        self.db.flush()
        return {
            "card": self._card_brief(card, grant),
            "shards_spent": cost["shards"],
            "redeem_points_spent": cost["redeem_points"],
            "coins_spent": coins_spent,
            "shard_balance": shard_row.amount,
            "redeem_points": user.redeem_points,
        }

    def upgrade_star(self, user: User, card_code: str, *, use_coin_fill: bool = False) -> dict[str, Any]:
        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == card_code).first()
        if not card:
            raise NotFoundError("卡牌不存在")
        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
            .with_for_update()
            .first()
        )
        if not row:
            raise BadRequestError("你尚未拥有该卡牌")
        if row.star >= MAX_STAR:
            raise BadRequestError("已达最高星级")

        next_star = row.star + 1
        cost = UPGRADE_STAR_COST.get(next_star)
        if not cost:
            raise BadRequestError("无法继续升星")

        shard_row = self._get_shard_row(user.id, card.rarity, for_update=True)
        coins_spent = 0
        shard_need = cost["shards"]
        shard_have = shard_row.amount or 0
        if shard_have < shard_need:
            deficit = shard_need - shard_have
            if not use_coin_fill:
                raise BadRequestError(f"碎片不足，需要 {shard_need} 个{card.rarity}碎片")
            coins_spent = self._buy_shards_with_coins(user, card.rarity, deficit)
            shard_row = self._get_shard_row(user.id, card.rarity, for_update=True)
        if (shard_row.amount or 0) < shard_need:
            raise BadRequestError(f"碎片不足，需要 {shard_need} 个{card.rarity}碎片")
        if (user.redeem_points or 0) < cost["redeem_points"]:
            raise BadRequestError(f"可用积分不足，需要 {cost['redeem_points']} 分")

        shard_row.amount -= cost["shards"]
        self.wallet.deduct_redeem_points(
            user, cost["redeem_points"], "collectible_upgrade", "collectible_card", card.id
        )
        row.star = next_star
        row.updated_at = _utcnow()
        self.db.flush()
        return {
            "card": self._card_detail(card, row),
            "new_star": next_star,
            "shards_spent": cost["shards"],
            "redeem_points_spent": cost["redeem_points"],
            "coins_spent": coins_spent,
            "shard_balance": shard_row.amount,
            "redeem_points": user.redeem_points,
        }

    def event_cheer_status(self, user: User) -> dict[str, Any]:
        """今日活动应援是否已完成（每队每日 1 次）。"""
        from app.services.collection_pass_service import CollectionPassService
        from app.services.arena_service import _team_date_ref

        if not user.favorite_team_id:
            return {
                "can_cheer": False,
                "cheered_today": False,
                "team_id": None,
                "team_name": None,
                "reason": "no_main_team",
            }
        events = CollectionPassService(self.db).get_active_events()
        if not events:
            return {
                "can_cheer": False,
                "cheered_today": False,
                "team_id": user.favorite_team_id,
                "team_name": None,
                "reason": "no_active_event",
            }
        team = self.db.get(Team, user.favorite_team_id)
        today = _utcnow().date()
        ref_id = _team_date_ref(user.favorite_team_id, today)
        existing = (
            self.db.query(CollectibleDropLog)
            .filter(
                CollectibleDropLog.user_id == user.id,
                CollectibleDropLog.source == "event_cheer",
                CollectibleDropLog.ref_type == "team_date",
                CollectibleDropLog.ref_id == ref_id,
            )
            .first()
        )
        cheered = existing is not None
        return {
            "can_cheer": not cheered,
            "cheered_today": cheered,
            "team_id": user.favorite_team_id,
            "team_name": team.name if team else None,
            "coin_cost": events[0].coin_action_cost,
            "event_code": events[0].code,
            "reason": None if not cheered else "already_cheered_today",
        }

    def event_cheer_drop(self, user: User, team_id: int) -> dict[str, Any]:
        from app.db.models import Team
        from app.services.arena_service import _team_date_ref
        from app.services.collection_pass_service import CollectionPassService

        if not self.db.get(Team, team_id):
            raise NotFoundError("球队不存在")
        if not user.favorite_team_id:
            raise BadRequestError("请先在个人资料设置主队")
        if team_id != user.favorite_team_id:
            raise BadRequestError("活动应援仅支持为你的主队应援")

        events = CollectionPassService(self.db).get_active_events()
        if not events:
            raise BadRequestError("当前无进行中的藏品活动")
        event = events[0]
        today = _utcnow().date()
        ref_id = _team_date_ref(team_id, today)

        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked

        existing = (
            self.db.query(CollectibleDropLog)
            .filter(
                CollectibleDropLog.user_id == user.id,
                CollectibleDropLog.source == "event_cheer",
                CollectibleDropLog.ref_type == "team_date",
                CollectibleDropLog.ref_id == ref_id,
            )
            .first()
        )
        if existing:
            payload = dict(
                existing.result_json
                or {"dropped": False, "cards": [], "shards": [], "source": "event_cheer"}
            )
            payload["already_claimed"] = True
            return payload

        self.wallet.deduct_coins(user, event.coin_action_cost, "event_cheer", "team_date", ref_id)
        boost = event.boost_json or {}
        forced_code = None
        if boost.get("forced_card_code"):
            forced_code = str(boost["forced_card_code"])
        elif random.random() < float(boost.get("forced_card_chance", 0.35)):
            card = (
                self.db.query(CollectibleCard)
                .filter(
                    CollectibleCard.active.is_(True),
                    CollectibleCard.series == event.event_series,
                )
                .first()
            )
            if card:
                forced_code = card.code
        if forced_code:
            result = self.drop_cards(
                user,
                "event_cheer",
                "team_date",
                ref_id,
                card_code=forced_code,
                team_boost_id=team_id,
            )
        else:
            result = self.drop_cards(
                user,
                "event_cheer",
                "team_date",
                ref_id,
                team_boost_id=team_id,
            )
        result["already_claimed"] = False
        return result

    def _buy_shards_with_coins(self, user: User, rarity: str, deficit: int) -> int:
        from app.core.config import get_settings
        from app.data.collection_pass_catalog import COIN_SHARD_FILL_COST, DAILY_COIN_SHARD_FILL_CAP
        from app.db.models.commerce import CollectionPassProgress
        from app.services.collection_pass_service import CollectionPassService

        settings = get_settings()
        deficit = max(1, min(int(deficit), settings.collection_pass_max_shard_deficit))
        unit = COIN_SHARD_FILL_COST.get(rarity, 5)
        cost = unit * deficit

        cp_svc = CollectionPassService(self.db)
        season = cp_svc._get_active_season()
        progress = cp_svc._get_or_create_progress(user, season)
        progress = (
            self.db.query(CollectionPassProgress)
            .filter(CollectionPassProgress.id == progress.id)
            .with_for_update()
            .one()
        )
        today = _utcnow().date()
        if progress.coin_shard_fill_date != today:
            progress.coin_shard_fill_date = today
            progress.coin_shard_fill_today = 0
        cap = DAILY_COIN_SHARD_FILL_CAP
        if (progress.coin_shard_fill_today or 0) + cost > cap:
            raise BadRequestError(f"今日球迷币补碎片已达上限（{cap} 币）")
        if (user.fan_coins or 0) < cost:
            raise BadRequestError(f"球迷币不足，补碎片需要 {cost} 币")
        progress.coin_shard_fill_today = (progress.coin_shard_fill_today or 0) + cost
        self.wallet.deduct_coins(user, cost, "collectible_shard_fill", "shard", hash(rarity) % 100000)
        self._add_shards(user.id, rarity, deficit)
        return cost

    def get_album(
        self,
        user: User,
        *,
        rarity: str | None = None,
        series: str | None = None,
        owned_only: bool = False,
        page: int = 1,
        limit: int = 60,
        brief: bool = True,
    ) -> dict[str, Any]:
        page = max(1, page)
        limit = min(max(1, limit), 120)
        shards = self.get_shards(user.id)

        base = self.db.query(CollectibleCard).filter(CollectibleCard.active.is_(True))
        if rarity:
            base = base.filter(CollectibleCard.rarity == rarity)
        if series:
            if series == "collab":
                from app.data.collab_catalog import COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL

                base = base.filter(CollectibleCard.series.in_([COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL]))
            else:
                base = base.filter(CollectibleCard.series == series)

        catalog_total = base.order_by(None).count()
        owned_q = (
            self.db.query(UserCollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.active.is_(True),
            )
        )
        if rarity:
            owned_q = owned_q.filter(CollectibleCard.rarity == rarity)
        if series:
            if series == "collab":
                from app.data.collab_catalog import COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL

                owned_q = owned_q.filter(CollectibleCard.series.in_([COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL]))
            else:
                owned_q = owned_q.filter(CollectibleCard.series == series)
        owned_total = owned_q.count()

        cards_out: list[dict[str, Any]] = []
        if owned_only:
            rows = (
                owned_q.options(joinedload(UserCollectibleCard.card))
                .order_by(CollectibleCard.sort_order, CollectibleCard.id)
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            for row in rows:
                card = row.card
                if not card:
                    continue
                item = (
                    self._card_album_brief(card, row)
                    if brief
                    else {**self._card_detail(card, row), "owned": True}
                )
                cards_out.append({**item, "owned": True})
            page_total = owned_total
        else:
            cards_page = (
                base.order_by(CollectibleCard.sort_order, CollectibleCard.id)
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            if cards_page:
                owned_rows = (
                    self.db.query(UserCollectibleCard)
                    .filter(
                        UserCollectibleCard.user_id == user.id,
                        UserCollectibleCard.card_id.in_([c.id for c in cards_page]),
                    )
                    .all()
                )
                owned_map: dict[int, list[UserCollectibleCard]] = {}
                for r in owned_rows:
                    owned_map.setdefault(r.card_id, []).append(r)
            else:
                owned_map = {}
            for card in cards_page:
                rows_for = owned_map.get(card.id)
                if rows_for:
                    primary = max(rows_for, key=lambda r: (r.star or 1, r.id))
                    total_count = sum(r.count or 1 for r in rows_for)
                    item = (
                        self._card_album_brief(card, primary)
                        if brief
                        else {**self._card_detail(card, primary), "owned": True}
                    )
                    item["count"] = total_count
                    if len(rows_for) > 1 or total_count > (primary.count or 1):
                        item["stack_instances"] = len(rows_for)
                    cards_out.append({**item, "owned": True})
                else:
                    cards_out.append(
                        {
                            **self._card_catalog_brief(card),
                            "owned": False,
                            "star": 0,
                            "count": 0,
                        }
                    )
            page_total = catalog_total

        has_more = page * limit < page_total
        return {
            "cards": cards_out,
            "page": page,
            "limit": limit,
            "page_total": page_total,
            "has_more": has_more,
            "total": catalog_total,
            "owned_count": owned_total,
            "completion_pct": round(owned_total / catalog_total * 100, 1) if catalog_total else 0,
            "shards": shards,
            "redeem_points": user.redeem_points or 0,
            "compliance_notice": COMPLIANCE_NOTICE,
            "chain_enabled": self._chain_enabled(),
            "series_options": self._series_options(),
        }

    def get_owned_preview(self, user: User, *, limit: int = 6, min_rarity: str = "rare") -> list[dict[str, Any]]:
        """Lightweight top owned cards for FanCard wall."""
        from sqlalchemy import case

        min_idx = RARITY_ORDER.index(min_rarity) if min_rarity in RARITY_ORDER else 1
        allowed = RARITY_ORDER[min_idx:]
        series_rank = case(
            (CollectibleCard.series == "pass_limited", 0),
            (CollectibleCard.series == "event_limited", 1),
            else_=2,
        )
        rarity_rank = case(
            (CollectibleCard.rarity == "legend", 0),
            (CollectibleCard.rarity == "epic", 1),
            (CollectibleCard.rarity == "rare", 2),
            (CollectibleCard.rarity == "common", 3),
            else_=4,
        )
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(
                UserCollectibleCard.user_id == user.id,
                CollectibleCard.active.is_(True),
                CollectibleCard.rarity.in_(allowed),
            )
            .order_by(series_rank, rarity_rank, CollectibleCard.sort_order, CollectibleCard.id)
            .limit(min(max(1, limit), 12))
            .all()
        )
        out = []
        for row, card in rows:
            out.append({**self._card_album_brief(card, row), "owned": True})
        return out

    def get_sets(self, user: User) -> list[dict]:
        sets = (
            self.db.query(CardSetDefinition)
            .filter(CardSetDefinition.active.is_(True))
            .order_by(CardSetDefinition.sort_order, CardSetDefinition.id)
            .all()
        )
        owned_codes = self._owned_card_codes(user.id)
        progress_rows = {
            p.set_id: p
            for p in self.db.query(CardSetProgress).filter(CardSetProgress.user_id == user.id).all()
        }
        all_missing: set[str] = set()
        set_payloads: list[tuple[Any, list[str], list[str]]] = []
        for s in sets:
            codes = list(s.card_codes or [])
            owned_in_set = [c for c in codes if c in owned_codes]
            missing = [c for c in codes if c not in owned_codes]
            all_missing.update(missing)
            set_payloads.append((s, owned_in_set, missing))

        name_map: dict[str, str] = {}
        if all_missing:
            name_rows = (
                self.db.query(CollectibleCard.code, CollectibleCard.name)
                .filter(CollectibleCard.code.in_(list(all_missing)))
                .all()
            )
            name_map = {r[0]: r[1] for r in name_rows}

        out = []
        for s, owned_in_set, missing in set_payloads:
            codes = list(s.card_codes or [])
            missing_names = [name_map.get(c, c) for c in missing]
            progress = progress_rows.get(s.id)
            out.append(
                {
                    "code": s.code,
                    "name": s.name,
                    "description": s.description,
                    "card_codes": codes,
                    "owned_codes": owned_in_set,
                    "missing_codes": missing,
                    "missing_names": missing_names,
                    "owned_count": len(owned_in_set),
                    "total_count": len(codes),
                    "complete": len(owned_in_set) >= len(codes) and len(codes) > 0,
                    "claimed": bool(progress and progress.claimed),
                    "reward": s.reward_json or {},
                }
            )
        return out

    def claim_set_reward(self, user: User, set_code: str) -> dict[str, Any]:
        sdef = self.db.query(CardSetDefinition).filter(CardSetDefinition.code == set_code).first()
        if not sdef:
            raise NotFoundError("套组不存在")

        owned_codes = self._owned_card_codes(user.id)
        codes = list(sdef.card_codes or [])
        if not codes or not all(c in owned_codes for c in codes):
            raise BadRequestError("套组尚未集齐")

        progress = (
            self.db.query(CardSetProgress)
            .filter(CardSetProgress.user_id == user.id, CardSetProgress.set_id == sdef.id)
            .with_for_update()
            .first()
        )
        if progress and progress.claimed:
            raise BadRequestError("奖励已领取")

        if not progress:
            progress = CardSetProgress(user_id=user.id, set_id=sdef.id)
            self.db.add(progress)

        reward = sdef.reward_json or {}
        if reward.get("badge_code"):
            self._award_badge(user, reward["badge_code"], reward.get("badge_title", "收藏家"))
        coins = int(reward.get("fan_coins") or 0)
        if coins > 0:
            self.wallet.add_coins(user, coins, "collectible_set_reward", "card_set", sdef.id)
        redeem_pts = int(reward.get("redeem_points") or 0)
        if redeem_pts > 0:
            self.wallet.add_redeem_points(user, redeem_pts, "collectible_set_reward", "card_set", sdef.id)

        progress.claimed = True
        progress.claimed_at = _utcnow()
        self.db.flush()
        self._notify_set_claimed(user, sdef)
        from app.services.collection_pass_service import CollectionPassService

        CollectionPassService.hook_award(
            user, self.db, "set_complete", "card_set", sdef.id, action="set_complete"
        )
        return {
            "set_code": set_code,
            "reward": reward,
            "fan_coins": user.fan_coins,
            "redeem_points": user.redeem_points,
        }

    def get_card_detail(self, user: User, card_code: str, *, user_card_id: int | None = None) -> dict[str, Any]:
        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == card_code).first()
        if not card:
            raise NotFoundError("卡牌不存在")
        q = self.db.query(UserCollectibleCard).filter(
            UserCollectibleCard.user_id == user.id,
            UserCollectibleCard.card_id == card.id,
        )
        if user_card_id:
            q = q.filter(UserCollectibleCard.id == user_card_id)
        rows = q.all()
        row = rows[0] if len(rows) == 1 else None
        if len(rows) > 1:
            if user_card_id:
                row = next((r for r in rows if r.id == user_card_id), rows[0])
            else:
                # 优先展示可流通的单卡，否则展示叠卡堆
                singles = [r for r in rows if (r.count or 1) == 1]
                stacks = [r for r in rows if (r.count or 1) > 1]
                row = singles[0] if singles else (stacks[0] if stacks else rows[0])
        total_count = sum(r.count or 1 for r in rows) if rows else 0
        detail = self._card_detail(card, row) if row else self._card_catalog_brief(card)
        detail["owned"] = row is not None
        detail["compliance_notice"] = COMPLIANCE_NOTICE
        if row and rows:
            detail["count"] = row.count or 1
            if len(rows) > 1 or total_count > (row.count or 1):
                detail["total_owned"] = total_count
                detail["split_instances"] = len(rows)
        if not row:
            detail["star"] = 0
            detail["count"] = 0
            detail["highlights"] = []
        return detail

    def get_shards(self, user_id: int) -> dict[str, int]:
        rows = self.db.query(CollectibleShard).filter(CollectibleShard.user_id == user_id).all()
        out = {r: 0 for r in RARITY_ORDER}
        for row in rows:
            out[row.rarity] = row.amount or 0
        return out

    def get_summary(self, user: User) -> dict[str, Any]:
        from sqlalchemy import case, func

        owned_count, failed_mints = (
            self.db.query(
                func.count(UserCollectibleCard.id),
                func.coalesce(
                    func.sum(case((UserCollectibleCard.chain_status == "failed", 1), else_=0)),
                    0,
                ),
            )
            .filter(UserCollectibleCard.user_id == user.id)
            .one()
        )
        total_active = self._total_active_cards()
        streak = int(user.signin_streak or 0)
        milestone_map = {3: "rare", 7: "epic", 14: "legend"}
        next_day = next((d for d in (3, 7, 14) if d > streak), None)
        owned_count = int(owned_count or 0)
        failed_mints = int(failed_mints or 0)
        return {
            "owned_count": owned_count,
            "total_cards": total_active,
            "completion_pct": round(owned_count / total_active * 100, 1) if total_active else 0,
            "shards": self.get_shards(user.id),
            "redeem_points": user.redeem_points or 0,
            "signin_streak": streak,
            "next_signin_milestone": (
                {
                    "day": next_day,
                    "days_left": next_day - streak,
                    "rarity": milestone_map[next_day],
                    "label": f"再签 {next_day - streak} 天得{milestone_map[next_day]}球星卡",
                }
                if next_day
                else None
            ),
            "hooks": {
                "predict_win": "猜中比赛掉落球星卡（主队加权）",
                "signin": "连签 3/7/14 天里程碑限定卡",
                "matchday": "比赛日动员有机会得主队球星卡",
                "referral": "邀请好友完成档案/首猜可得限定卡",
            },
            "chain_enabled": self._chain_enabled(),
            "failed_mints": failed_mints,
            "compliance_notice": COMPLIANCE_NOTICE,
        }

    def get_recent_activity(self, user: User, *, limit: int = 15) -> list[dict[str, Any]]:
        rows = (
            self.db.query(CollectibleDropLog)
            .filter(CollectibleDropLog.user_id == user.id)
            .order_by(CollectibleDropLog.id.desc())
            .limit(min(limit, 50))
            .all()
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            payload = row.result_json or {}
            if not payload.get("dropped"):
                continue
            cards = payload.get("cards") or []
            out.append(
                {
                    "source": row.source,
                    "at": row.created_at.isoformat() if row.created_at else None,
                    "cards": cards,
                    "shards": payload.get("shards") or [],
                }
            )
        return out

    def get_cost_tables(self) -> dict[str, Any]:
        return {
            "synthesis": SYNTHESIS_COST,
            "upgrade_star": UPGRADE_STAR_COST,
            "shard_on_duplicate": SHARD_ON_DUPLICATE,
        }

    def apply_match_highlight(self, match: Match) -> int:
        """Light up highlight marks on owned cards for scorers/assisters."""
        if match.status != "finished":
            return 0
        events = match.events_json if isinstance(match.events_json, list) else []
        if not events:
            return self._apply_final_score_highlight(match)

        player_names: set[str] = set()
        for ev in events:
            if not isinstance(ev, dict):
                continue
            ev_type = str(ev.get("type") or ev.get("detail") or "").lower()
            if "goal" in ev_type or "assist" in ev_type:
                player = ev.get("player") or ev.get("player_name") or ev.get("name")
                if player:
                    player_names.add(str(player).strip())

        if not player_names:
            return self._apply_final_score_highlight(match)

        team_ids = self._match_team_ids(match.id)
        players = (
            self.db.query(PlayerDetailed)
            .filter(PlayerDetailed.team_id.in_(team_ids), PlayerDetailed.name.in_(list(player_names)))
            .all()
        )
        if not players:
            return 0

        player_ids = [p.id for p in players]
        cards = self.db.query(CollectibleCard).filter(CollectibleCard.player_id.in_(player_ids)).all()
        if not cards:
            return 0

        card_ids = [c.id for c in cards]
        rows = self.db.query(UserCollectibleCard).filter(UserCollectibleCard.card_id.in_(card_ids)).all()
        updated = 0
        highlight_entry = {
            "match_id": match.id,
            "team1": match.team1_name,
            "team2": match.team2_name,
            "score": f"{match.home_score}:{match.away_score}",
            "at": _utcnow().isoformat(),
            "type": "match_highlight",
        }
        for row in rows:
            highlights = list(row.highlight_json or [])
            if any(h.get("match_id") == match.id for h in highlights if isinstance(h, dict)):
                continue
            highlights.append(highlight_entry)
            row.highlight_json = highlights
            row.updated_at = _utcnow()
            updated += 1
        return updated

    def apply_match_highlights_batch(self) -> int:
        from sqlalchemy import desc

        matches = (
            self.db.query(Match)
            .filter(Match.status == "finished")
            .order_by(desc(Match.id))
            .limit(30)
            .all()
        )
        total = 0
        for m in matches:
            total += self.apply_match_highlight(m)
        if total:
            self.db.commit()
        return total

    def _apply_final_score_highlight(self, match: Match) -> int:
        if match.home_score is None or match.away_score is None:
            return 0
        team_ids = self._match_team_ids(match.id)
        cards = self.db.query(CollectibleCard).filter(CollectibleCard.team_id.in_(team_ids)).all()
        if not cards:
            return 0
        card_ids = [c.id for c in cards if c.series == "team_crest"]
        rows = self.db.query(UserCollectibleCard).filter(UserCollectibleCard.card_id.in_(card_ids)).all()
        updated = 0
        entry = {
            "match_id": match.id,
            "team1": match.team1_name,
            "team2": match.team2_name,
            "score": f"{match.home_score}:{match.away_score}",
            "at": _utcnow().isoformat(),
            "type": "team_match",
        }
        for row in rows:
            highlights = list(row.highlight_json or [])
            if any(h.get("match_id") == match.id for h in highlights if isinstance(h, dict)):
                continue
            highlights.append(entry)
            row.highlight_json = highlights
            updated += 1
        return updated

    def _match_team_ids(self, match_id: int) -> set[int]:
        match = self.db.get(Match, match_id)
        if not match:
            return set()
        ids: set[int] = set()
        for name in (match.team1_name, match.team2_name):
            if not name:
                continue
            team = self.db.query(Team).filter(Team.name == name).first()
            if team:
                ids.add(team.id)
        return ids

    def _is_card_available(
        self, card: CollectibleCard, source: str, *, event_boost: dict | None = None
    ) -> bool:
        now = _utcnow()
        if card.available_from and now < card.available_from:
            return False
        if card.available_until and now > card.available_until:
            return False
        if card.is_limited and source == "predict_win":
            return False
        if card.series == "matchday_limited" and source != "matchday":
            return False
        if card.series == "pass_limited" and source != "collection_pass":
            return False
        if card.series == "event_limited" and source not in ("event_cheer", "matchday"):
            return False
        if card.series == "event_limited" and source == "matchday":
            boost = event_boost if event_boost is not None else self._active_event_boost()
            if not boost:
                return False
        return True

    def _apply_source_series_sql(self, q, source: str):
        if source == "collection_pass":
            return q.filter(CollectibleCard.series == "pass_limited")
        if source == "matchday":
            return q.filter(CollectibleCard.series != "pass_limited")
        return q.filter(CollectibleCard.series.notin_(["pass_limited", "matchday_limited"]))

    def _series_options(self) -> list[dict[str, str]]:
        if _catalog_cache["series_options"] is not None:
            return _catalog_cache["series_options"]
        rows = (
            self.db.query(CollectibleCard.series)
            .filter(CollectibleCard.active.is_(True))
            .distinct()
            .order_by(CollectibleCard.series)
            .all()
        )
        labels = {
            "legend": "传奇",
            "team_crest": "队徽",
            "team_squad": "球星",
            "group": "小组",
            "matchday_limited": "比赛日限定",
            "pass_limited": "手册限定",
            "event_limited": "活动限定",
            "club_collab": "联名·俱乐部",
            "kol_special": "联名·IP",
        }
        options = [{"value": r[0], "label": labels.get(r[0], r[0])} for r in rows if r[0]]
        has_collab = any(r[0] in ("club_collab", "kol_special") for r in rows)
        if has_collab and not any(o["value"] == "collab" for o in options):
            options.insert(0, {"value": "collab", "label": "联名/IP"})
        _catalog_cache["series_options"] = options
        return options

    def get_chain_status(self, user: User) -> dict[str, Any]:
        from sqlalchemy import func

        from app.core.config import get_settings
        from app.db.models.commerce import UserChainAccount

        settings = get_settings()
        counts = dict(
            self.db.query(UserCollectibleCard.chain_status, func.count())
            .filter(UserCollectibleCard.user_id == user.id)
            .group_by(UserCollectibleCard.chain_status)
            .all()
        )
        pending = counts.get("pending", 0) + counts.get("minting", 0)
        acct = None
        if settings.avata_active:
            row = self.db.query(UserChainAccount).filter(UserChainAccount.user_id == user.id).first()
            if row:
                acct = {
                    "native_address": row.native_address,
                    "status": row.status,
                    "chain_name": row.chain_name,
                }
        return {
            "enabled": settings.avata_active,
            "chain_name": settings.avata_chain_name,
            "mock": settings.avata_mock,
            "pending_mints": pending,
            "minted_count": counts.get("minted", 0),
            "failed_mints": counts.get("failed", 0),
            "account": acct,
            "compliance_notice": "文昌链数字藏品由 AVATA 平台托管，仅限平台内展示，不可转赠交易。",
        }

    def _total_active_cards(self) -> int:
        if _catalog_cache["total_active"] is not None:
            return int(_catalog_cache["total_active"])
        total = self.db.query(CollectibleCard).filter(CollectibleCard.active.is_(True)).count()
        _catalog_cache["total_active"] = total
        return total

    def _active_event_boost(self) -> dict:
        if self._event_boost_cached is not None:
            return self._event_boost_cached
        try:
            from app.core.cache import cache_get
            from app.services.collection_pass_service import EVENTS_CACHE_KEY, CollectionPassService

            cached = cache_get(EVENTS_CACHE_KEY)
            if cached and isinstance(cached, list) and cached:
                boost = cached[0].get("boost_json") or {}
                self._event_boost_cached = boost
                return boost
            events = CollectionPassService(self.db).get_active_events()
            if events:
                boost = events[0].boost_json or {}
                self._event_boost_cached = boost
                return boost
        except Exception:
            pass
        self._event_boost_cached = {}
        return {}

    def _roll_rarity(self, source: str) -> str:
        weights = DROP_WEIGHTS_BY_SOURCE.get(source, DROP_WEIGHTS_BY_SOURCE["predict_win"])
        roll = random.random()
        cumulative = 0.0
        for rarity in RARITY_ORDER:
            cumulative += weights.get(rarity, 0)
            if roll <= cumulative:
                return rarity
        return "common"

    def _pick_card(
        self,
        rarity: str,
        boost_team_id: int | None,
        match_team_ids: set[int],
        source: str,
    ) -> CollectibleCard | None:
        q = self._apply_source_series_sql(
            self.db.query(CollectibleCard).filter(
                CollectibleCard.active.is_(True),
                CollectibleCard.rarity == rarity,
            ),
            source,
        )
        if source == "signin" and rarity == "legend":
            q = q.filter(CollectibleCard.series == "legend")
        event_boost = self._active_event_boost()
        if source == "matchday" and boost_team_id:
            limited = (
                self.db.query(CollectibleCard)
                .filter(
                    CollectibleCard.active.is_(True),
                    CollectibleCard.rarity == rarity,
                    CollectibleCard.team_id == boost_team_id,
                    CollectibleCard.series == "matchday_limited",
                )
                .first()
            )
            if limited and self._is_card_available(limited, source, event_boost=event_boost):
                return limited
        candidates = q.limit(300).all()
        candidates = [c for c in candidates if self._is_card_available(c, source, event_boost=event_boost)]
        if not candidates:
            return None

        weighted: list[tuple[CollectibleCard, float]] = []
        for card in candidates:
            weight = 1.0
            if boost_team_id and card.team_id == boost_team_id:
                weight *= 2.5
            if match_team_ids and card.team_id in match_team_ids:
                weight *= 2.0
            if card.series == "legend":
                weight *= 0.5
            if source == "matchday" and card.series == "matchday_limited":
                weight *= 3.0
            if source == "event_cheer" and card.series == "event_limited":
                weight *= float(event_boost.get("series_weight", 3.0))
            if source == "matchday" and card.series == "event_limited" and event_boost:
                weight *= float(event_boost.get("matchday_series_weight", 2.0))
            weighted.append((card, weight))

        total = sum(w for _, w in weighted)
        if total <= 0:
            return random.choice(candidates)
        roll = random.random() * total
        cumulative = 0.0
        for card, weight in weighted:
            cumulative += weight
            if roll <= cumulative:
                return card
        return weighted[-1][0]

    def _grant_card(
        self,
        user: User,
        card: CollectibleCard,
        source: str,
        *,
        increment: bool = True,
    ) -> dict[str, Any]:
        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
            .with_for_update()
            .first()
        )
        if row:
            if increment:
                row.count = (row.count or 1) + 1
            row.updated_at = _utcnow()
            return {"is_duplicate": True, "star": row.star, "count": row.count}
        row = UserCollectibleCard(
            user_id=user.id,
            card_id=card.id,
            star=1,
            count=1,
            source=source,
            highlight_json=[],
        )
        self.db.add(row)
        self.db.flush()
        # 资产化：分配序列号、设估值、冷却期
        try:
            from app.data.asset_catalog import estimate_card_value
            from app.services.card_asset_service import CardAssetService

            asset = CardAssetService(self.db)
            serial, mint_total = asset.assign_serial(card.id)
            row.serial_no = serial
            if mint_total:
                row.mint_total = mint_total
            row.acquired_value = estimate_card_value(card.rarity, 1, serial_no=serial, mint_total=mint_total)
            asset.apply_cooldown(row)
        except Exception:
            logger.exception("Collectible serial assign failed user=%s card=%s", user.id, card.id)
        try:
            from app.services.collectible_chain_service import CollectibleChainService

            CollectibleChainService(self.db).queue_mint(user, row, card)
        except Exception:
            logger.exception("Collectible chain queue failed user=%s card=%s", user.id, card.id)
        return {"is_duplicate": False, "star": 1, "count": 1, "user_card_id": row.id}

    def _add_shards(self, user_id: int, rarity: str, amount: int) -> None:
        if amount <= 0:
            return
        row = self._get_shard_row(user_id, rarity, for_update=True)
        row.amount = (row.amount or 0) + amount

    def _get_shard_row(self, user_id: int, rarity: str, *, for_update: bool = False) -> CollectibleShard:
        q = self.db.query(CollectibleShard).filter(
            CollectibleShard.user_id == user_id,
            CollectibleShard.rarity == rarity,
        )
        if for_update:
            q = q.with_for_update()
        row = q.first()
        if not row:
            row = CollectibleShard(user_id=user_id, rarity=rarity, amount=0)
            self.db.add(row)
            self.db.flush()
        return row

    def _save_drop_log(
        self,
        user_id: int,
        source: str,
        ref_type: str,
        ref_id: int,
        result: dict,
    ) -> int | None:
        try:
            with self.db.begin_nested():
                row = CollectibleDropLog(
                    user_id=user_id,
                    source=source,
                    ref_type=ref_type,
                    ref_id=ref_id,
                    result_json=result,
                )
                self.db.add(row)
                self.db.flush()
                return row.id
        except IntegrityError:
            existing = (
                self.db.query(CollectibleDropLog)
                .filter(
                    CollectibleDropLog.user_id == user_id,
                    CollectibleDropLog.source == source,
                    CollectibleDropLog.ref_type == ref_type,
                    CollectibleDropLog.ref_id == ref_id,
                )
                .first()
            )
            if existing and existing.result_json:
                return None
            raise

    def _notify_drop(self, user: User, result: dict[str, Any], log_id: int | None) -> None:
        if not log_id or not result.get("dropped"):
            return
        try:
            from app.services.notification_service import NotificationService

            NotificationService(self.db).notify_collectible_drop(
                user.id,
                drop_log_id=log_id,
                result=result,
            )
        except Exception:
            logger.exception("Collectible drop notification failed user=%s", user.id)

    def _notify_set_claimed(self, user: User, sdef: CardSetDefinition) -> None:
        try:
            from app.services.notification_service import NotificationService

            NotificationService(self.db).notify_collectible_set_claimed(
                user.id,
                set_id=sdef.id,
                set_name=sdef.name,
                reward=sdef.reward_json or {},
            )
        except Exception:
            logger.exception("Collectible set claim notification failed user=%s set=%s", user.id, sdef.code)

    def _owned_card_codes(self, user_id: int) -> set[str]:
        rows = (
            self.db.query(CollectibleCard.code)
            .join(UserCollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user_id)
            .all()
        )
        return {r[0] for r in rows}

    def _user_owns_card(self, user_id: int, card_id: int) -> bool:
        return (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user_id, UserCollectibleCard.card_id == card_id)
            .first()
            is not None
        )

    def _award_badge(self, user: User, code: str, title: str) -> None:
        exists = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == user.id, UserBadge.badge_code == code)
            .first()
        )
        if not exists:
            self.db.add(UserBadge(user_id=user.id, badge_code=code, title=title))

    def _card_album_brief(self, card: CollectibleCard, row: UserCollectibleCard) -> dict[str, Any]:
        """List view: minimal fields, chain status only (no nft ids)."""
        chain_status = row.chain_status if self._chain_enabled() and row.chain_status else None
        chain = None
        if chain_status and chain_status not in ("none", ""):
            chain = {
                "enabled": True,
                "chain_name": get_settings().avata_chain_name if self._chain_enabled() else "文昌链",
                "status": chain_status,
            }
        return {
            "code": card.code,
            "name": card.name,
            "rarity": card.rarity,
            "series": card.series,
            "image_url": card.image_url,
            "star": row.star,
            "count": row.count,
            "user_card_id": row.id,
            "chain": chain,
        }

    def _card_catalog_brief(self, card: CollectibleCard) -> dict[str, Any]:
        return {
            "code": card.code,
            "name": card.name,
            "rarity": card.rarity,
            "series": card.series,
            "image_url": card.image_url,
            "attributes": card.attributes_json or {},
            "player_id": card.player_id,
            "team_id": card.team_id,
        }

    def _card_brief(self, card: CollectibleCard, grant: dict) -> dict[str, Any]:
        return {
            **self._card_catalog_brief(card),
            "star": grant.get("star", 1),
            "count": grant.get("count", 1),
            "is_duplicate": grant.get("is_duplicate", False),
        }

    def _card_detail(self, card: CollectibleCard, row: UserCollectibleCard) -> dict[str, Any]:
        detail = {
            **self._card_catalog_brief(card),
            "star": row.star,
            "count": row.count,
            "source": row.source,
            "highlights": list(row.highlight_json or []),
            "obtained_at": row.obtained_at.isoformat() if row.obtained_at else None,
            "user_card_id": row.id,
        }
        # 资产化字段
        detail["asset"] = self._asset_brief(card, row)
        chain = self._chain_brief(row)
        if chain:
            detail["chain"] = chain
        if row.star < MAX_STAR:
            next_star = row.star + 1
            cost = UPGRADE_STAR_COST.get(next_star)
            if cost:
                shard_bal = self.get_shards(row.user_id)
                owner = self.db.get(User, row.user_id)
                detail["upgrade_cost"] = cost
                detail["can_upgrade"] = (
                    shard_bal.get(card.rarity, 0) >= cost["shards"]
                    and owner is not None
                    and (owner.redeem_points or 0) >= cost["redeem_points"]
                )
        return detail

    def _asset_brief(self, card: CollectibleCard, row: UserCollectibleCard) -> dict[str, Any]:
        try:
            from app.core.config import get_settings
            from app.data.asset_catalog import estimate_card_value
            from app.services.card_asset_service import CardAssetService

            if not row.serial_no:
                try:
                    CardAssetService(self.db).backfill_serial(row)
                    self.db.flush()
                except Exception:
                    logger.exception("serial backfill failed row=%s", row.id)

            settings = get_settings()
            now = _utcnow()
            cooling = bool(row.holding_until and row.holding_until > now)
            buyback_floor = settings.asset_buyback_floor_map.get(card.rarity, 0)
            buyback_mult = {1: 1.0, 2: 1.4, 3: 2.0}.get(int(row.star or 1), 1.0)
            stack_count = row.count or 1
            return {
                "card_id": card.id,
                "serial_no": row.serial_no,
                "mint_total": row.mint_total,
                "tradable": bool(row.tradable) and stack_count <= 1,
                "stack_count": stack_count,
                "lock_state": row.lock_state or "none",
                "holding_until": row.holding_until.isoformat() if row.holding_until else None,
                "cooling_down": cooling,
                "estimated_value": estimate_card_value(
                    card.rarity, row.star, serial_no=row.serial_no, mint_total=row.mint_total
                ),
                "buyback_quote": int(buyback_floor * buyback_mult),
                "currency": "redeem_points",
            }
        except Exception:
            logger.exception("asset brief failed card=%s", card.id)
            return {}

    def _chain_enabled(self) -> bool:
        try:
            from app.core.config import get_settings

            return get_settings().avata_active
        except Exception:
            return False

    def _chain_brief(self, row: UserCollectibleCard) -> dict[str, Any] | None:
        try:
            from app.services.collectible_chain_service import CollectibleChainService

            return CollectibleChainService(self.db).chain_brief(row)
        except Exception:
            return None

    def synthesis_options(self, user: User) -> list[dict]:
        owned_ids = {
            r[0]
            for r in self.db.query(UserCollectibleCard.card_id)
            .filter(UserCollectibleCard.user_id == user.id)
            .all()
        }
        shards = self.get_shards(user.id)
        active_rarities = [r for r in RARITY_ORDER if r != "legend" and shards.get(r, 0) > 0]
        if not active_rarities:
            return []
        cards = (
            self.db.query(CollectibleCard)
            .filter(
                CollectibleCard.active.is_(True),
                CollectibleCard.rarity.in_(active_rarities),
            )
            .order_by(CollectibleCard.rarity, CollectibleCard.sort_order)
            .limit(200)
            .all()
        )
        out = []
        for card in cards:
            if card.id in owned_ids:
                continue
            cost = SYNTHESIS_COST.get(card.rarity)
            if not cost:
                continue
            out.append(
                {
                    **self._card_catalog_brief(card),
                    "cost": cost,
                    "can_synthesize": (shards.get(card.rarity, 0) >= cost["shards"]
                                       and (user.redeem_points or 0) >= cost["redeem_points"]),
                }
            )
        return out

    def seed_collab_cards(self) -> dict[str, int]:
        """幂等创建联名/IP 卡牌 catalog。"""
        from app.data.collab_catalog import COLLAB_CARDS

        created = updated = 0
        for spec in COLLAB_CARDS:
            row = (
                self.db.query(CollectibleCard).filter(CollectibleCard.code == spec["code"]).first()
            )
            attrs = {"mint_total": spec.get("mint_total"), "collab": True}
            if not row:
                row = CollectibleCard(
                    code=spec["code"],
                    name=spec["name"],
                    rarity=spec["rarity"],
                    series=spec["series"],
                    image_url=spec.get("image_url"),
                    active=True,
                    attributes_json=attrs,
                    sort_order=900,
                )
                self.db.add(row)
                created += 1
            else:
                row.name = spec["name"]
                row.rarity = spec["rarity"]
                row.series = spec["series"]
                if spec.get("image_url"):
                    row.image_url = spec["image_url"]
                row.attributes_json = {**(row.attributes_json or {}), **attrs}
                row.active = True
                updated += 1
        self.db.commit()
        return {"created": created, "updated": updated}
