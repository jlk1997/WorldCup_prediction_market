"""卡牌对决 PVP — 异步选卡比战力（可用积分入场）。"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.data.combat_stats import build_combat_attrs, normalize_position
from app.db.models.commerce import (
    CardDuel,
    CardDuelLog,
    CardStake,
    CollectibleCard,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository
from app.services.card_asset_service import CardAssetService
from app.services.combat_engine import (
    battle_power,
    bp_tier,
    build_combat_card_from_row,
    build_combat_card_from_virtual,
    deck_average_bp,
    deck_summary,
    resolve_duel,
)

logger = logging.getLogger(__name__)

DUEL_CARD_COUNT = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CardDuelService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)
        self.asset = CardAssetService(db)

    def _lock_user(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).with_for_update().first()

    def _lock_users_ordered(self, *user_ids: int) -> dict[int, User]:
        """按 user_id 升序加锁，避免并发 accept 死锁。"""
        locked: dict[int, User] = {}
        for uid in sorted({u for u in user_ids if u}):
            row = self._lock_user(uid)
            if not row:
                raise NotFoundError("用户不存在")
            locked[uid] = row
        return locked

    def _staked_card_ids(self, user_id: int) -> set[int]:
        return {
            s.user_card_id
            for s in self.db.query(CardStake.user_card_id)
            .filter(CardStake.user_id == user_id, CardStake.status == "active")
            .all()
        }

    def _pending_pvp_card_ids(self, *, exclude_duel_id: int | None = None) -> set[int]:
        q = self.db.query(CardDuel).filter(
            CardDuel.status == "pending",
            CardDuel.mode == "pvp",
        )
        if exclude_duel_id:
            q = q.filter(CardDuel.id != exclude_duel_id)
        used: set[int] = set()
        for d in q.all():
            for cid in d.challenger_card_ids or []:
                if cid:
                    used.add(int(cid))
        return used

    def _count_user_pending_pvp(self, user_id: int, *, as_challenger: bool = True) -> int:
        q = self.db.query(CardDuel.id).filter(
            CardDuel.status == "pending",
            CardDuel.mode == "pvp",
        )
        if as_challenger:
            q = q.filter(CardDuel.challenger_id == user_id)
        else:
            q = q.filter(CardDuel.defender_id == user_id)
        return q.count()

    def _apply_duel_locks(self, rows: list[UserCollectibleCard]) -> None:
        for row in rows:
            row.lock_state = "duel"

    def _release_duel_locks(self, card_ids: list[int] | None) -> None:
        if not card_ids:
            return
        for cid in card_ids:
            row = self.db.get(UserCollectibleCard, cid)
            if row and (row.lock_state or "none") == "duel":
                row.lock_state = "none"

    def _refund_challenger_stake(self, duel: CardDuel, challenger: User) -> None:
        stake = duel.stake_points or 0
        if stake <= 0:
            return
        self.wallet.add_redeem_points(
            challenger, stake, "duel_stake_refund", "card_duel", duel.id
        )

    def eligible_cards(self, user: User, *, minted_only: bool = False) -> list[dict[str, Any]]:
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user.id)
            .all()
        )
        staked_ids = {
            s.user_card_id
            for s in self.db.query(CardStake.user_card_id)
            .filter(CardStake.user_id == user.id, CardStake.status == "active")
            .all()
        }
        out = []
        for row, card in rows:
            if (row.count or 1) > 1:
                continue
            if row.lock_state and row.lock_state != "none":
                continue
            if row.id in staked_ids:
                continue
            if minted_only and (row.chain_status or "none") != "minted":
                continue
            attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
            power = self._card_power(row, card)
            out.append(
                {
                    "user_card_id": row.id,
                    "name": card.name,
                    "rarity": card.rarity,
                    "image_url": card.image_url,
                    "star": row.star,
                    "rating": attrs.get("overall_rating"),
                    "position": normalize_position(attrs.get("position")),
                    "power": power,
                    "bp": power,
                    "combat_stats": attrs.get("combat_stats"),
                    "chain_status": row.chain_status or "none",
                }
            )
        return sorted(out, key=lambda x: -x["power"])

    def _card_power(self, row: UserCollectibleCard, card: CollectibleCard) -> int:
        cc = build_combat_card_from_row(row, card)
        return battle_power(cc)

    def _deck_average_bp(self, rows: list[UserCollectibleCard]) -> float:
        cards = []
        for row in rows:
            card = self.db.get(CollectibleCard, row.card_id)
            if card:
                cards.append(build_combat_card_from_row(row, card))
        return deck_average_bp(cards)

    def _bp_tier(self, avg_bp: float) -> int:
        return bp_tier(avg_bp)

    def _estimate_ai_elo(self, duel: CardDuel) -> int:
        ai_deck = duel.ai_deck_json or []
        if not ai_deck:
            return 1000
        bps = [float(c.get("bp") or c.get("power") or 200) for c in ai_deck]
        avg = sum(bps) / len(bps)
        return max(800, min(1600, int(1000 + (avg - 250) * 1.5)))

    def _apply_duel_elo(
        self,
        duel: CardDuel,
        challenger: User,
        defender: User | None,
        winner_id: int | None,
    ) -> tuple[int, int]:
        from app.services.duel_elo_service import DEFAULT_ELO, apply_ai_elo, apply_pvp_elo

        if not winner_id:
            return 0, 0

        ch_elo = int(challenger.duel_elo or DEFAULT_ELO)
        if duel.mode == "pvp" and defender and duel.defender_id:
            def_elo = int(defender.duel_elo or DEFAULT_ELO)
            deltas = apply_pvp_elo(
                ch_elo, def_elo, winner_id, duel.challenger_id, duel.defender_id
            )
            ch_delta = deltas["challenger_delta"]
            def_delta = deltas["defender_delta"]
            duel.challenger_elo_delta = ch_delta
            duel.defender_elo_delta = def_delta
            challenger.duel_elo = max(100, ch_elo + ch_delta)
            defender.duel_elo = max(100, def_elo + def_delta)
            return ch_delta, def_delta

        if duel.mode == "ai":
            ai_elo = self._estimate_ai_elo(duel)
            player_won = winner_id == duel.challenger_id
            ch_delta = apply_ai_elo(ch_elo, ai_elo, player_won)
            duel.challenger_elo_delta = ch_delta
            duel.defender_elo_delta = 0
            challenger.duel_elo = max(100, ch_elo + ch_delta)
            return ch_delta, 0

        return 0, 0

    def _lifetime_duel_count(self, user_id: int) -> int:
        return (
            self.db.query(CardDuel.id)
            .filter(
                CardDuel.status == "settled",
                (CardDuel.challenger_id == user_id) | (CardDuel.defender_id == user_id),
            )
            .count()
        )

    def _duels_today_count(self, user_id: int) -> int:
        today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(CardDuel.id)
            .filter(
                CardDuel.status == "settled",
                CardDuel.settled_at >= today_start,
                (CardDuel.challenger_id == user_id) | (CardDuel.defender_id == user_id),
            )
            .count()
        )

    def _duel_win_streak(self, user_id: int) -> int:
        rows = (
            self.db.query(CardDuel)
            .filter(
                CardDuel.status == "settled",
                (CardDuel.challenger_id == user_id) | (CardDuel.defender_id == user_id),
            )
            .order_by(CardDuel.id.desc())
            .limit(10)
            .all()
        )
        streak = 0
        for d in rows:
            if d.winner_id == user_id:
                streak += 1
            else:
                break
        return streak

    def _winner_card_ids(self, duel: CardDuel, winner_id: int) -> list[int]:
        if winner_id == duel.challenger_id:
            return list(duel.challenger_card_ids or [])
        return list(duel.defender_card_ids or [])

    def _deck_all_minted(self, duel: CardDuel, winner_id: int) -> bool:
        ids = self._winner_card_ids(duel, winner_id)
        if len(ids) != DUEL_CARD_COUNT:
            return False
        rows = self.db.query(UserCollectibleCard).filter(UserCollectibleCard.id.in_(ids)).all()
        if len(rows) != DUEL_CARD_COUNT:
            return False
        return all((r.chain_status or "none") == "minted" for r in rows)

    def _record_duel_fee_sink(self, amount: int, duel_id: int) -> None:
        if amount <= 0:
            return
        try:
            from app.services.product_analytics_service import ProductAnalyticsService

            ProductAnalyticsService(self.db).track(
                "duel_fee_sink",
                payload={"amount": amount, "duel_id": duel_id},
                commit=False,
            )
        except Exception:
            logger.debug("duel_fee_sink track skipped")

    def _award_duel_loss_comfort(self, user: User, duel_id: int) -> None:
        from app.db.models.commerce import CollectibleDropLog
        from app.data.collectible_catalog import SHARD_ON_DUPLICATE
        from app.services.collectible_service import CollectibleService

        today_key = int(_utcnow().strftime("%Y%m%d"))
        existing = (
            self.db.query(CollectibleDropLog)
            .filter(
                CollectibleDropLog.user_id == user.id,
                CollectibleDropLog.source == "duel_loss_comfort",
                CollectibleDropLog.ref_type == "duel_daily_loss",
                CollectibleDropLog.ref_id == today_key,
            )
            .first()
        )
        if existing:
            return
        shard_amount = SHARD_ON_DUPLICATE.get("common", 5)
        svc = CollectibleService(self.db)
        svc._add_shards(user.id, "common", shard_amount)
        result = {
            "dropped": False,
            "cards": [],
            "shards": [{"rarity": "common", "amount": shard_amount, "reason": "duel_loss"}],
            "source": "duel_loss_comfort",
            "chain_enabled": svc._chain_enabled(),
        }
        svc._save_drop_log(user.id, "duel_loss_comfort", "duel_daily_loss", today_key, result)
        try:
            from app.services.collection_pass_service import CollectionPassService

            CollectionPassService.hook_award(
                user, self.db, "duel_complete", "card_duel", duel_id, action="duel_complete"
            )
        except Exception:
            logger.debug("duel pass hook loser skipped")

    def _award_duel_win_drops(self, user: User, duel: CardDuel) -> dict[str, Any] | None:
        from app.services.collectible_service import CollectibleService

        svc = CollectibleService(self.db)
        primary: dict[str, Any] | None = None
        today_key = int(_utcnow().strftime("%Y%m%d"))

        daily = svc.drop_cards(user, "duel_daily_win", "duel_daily", today_key)
        if daily.get("dropped"):
            primary = daily

        streak = self._duel_win_streak(user.id)
        if streak >= 3:
            streak_drop = svc.drop_cards(user, "duel_streak", "duel_streak", streak)
            if streak_drop.get("dropped") and not primary:
                primary = streak_drop

        if random.random() < self.settings.card_duel_win_drop_chance:
            win_drop = svc.drop_cards(user, "duel_win", "card_duel", duel.id)
            if win_drop.get("dropped") and not primary:
                primary = win_drop

        if self._deck_all_minted(duel, user.id):
            chain_drop = svc.drop_cards(user, "duel_chain_bonus", "card_duel_chain", duel.id)
            if chain_drop.get("dropped") and not primary:
                primary = chain_drop

        try:
            from app.services.collection_pass_service import CollectionPassService

            CollectionPassService.hook_award(user, self.db, "duel_win", "card_duel", duel.id, action="duel_win")
            CollectionPassService.hook_award(
                user, self.db, "duel_complete", "card_duel", duel.id, action="duel_complete"
            )
        except Exception:
            logger.debug("duel pass hook skipped")

        return primary

    def _primary_mint_boost_pct(self, user_card_id: int) -> float:
        from app.db.models.commerce import CardTransferLog

        cutoff = _utcnow() - timedelta(days=self.settings.mint_primary_boost_days)
        exists = (
            self.db.query(CardTransferLog.id)
            .filter(
                CardTransferLog.user_card_id == user_card_id,
                CardTransferLog.kind == "primary",
                CardTransferLog.created_at >= cutoff,
            )
            .first()
        )
        if exists:
            return float(self.settings.mint_primary_duel_bp_bonus_pct) / 100.0
        return 0.0

    def _load_user_combat_cards(self, card_ids: list[int], user_id: int, *, side: str) -> list:
        cards = []
        for cid in card_ids:
            row = self.db.get(UserCollectibleCard, cid)
            if not row or row.user_id != user_id:
                continue
            card = self.db.get(CollectibleCard, row.card_id)
            if card:
                chem = self._primary_mint_boost_pct(row.id)
                cards.append(
                    build_combat_card_from_row(row, card, side=side, chemistry_bonus_pct=chem)
                )
        return cards

    def _generate_ai_deck(self, challenger_rows: list[UserCollectibleCard]) -> list[dict]:
        """按挑战者卡组平均 BP 从 catalog 生成 AI 对手。"""
        target_bp = self._deck_average_bp(challenger_rows) or 200.0
        lo, hi = target_bp * 0.85, target_bp * 1.15
        catalog = (
            self.db.query(CollectibleCard)
            .filter(CollectibleCard.active.is_(True), CollectibleCard.series == "team_squad")
            .limit(200)
            .all()
        )
        if len(catalog) < 3:
            catalog = self.db.query(CollectibleCard).filter(CollectibleCard.active.is_(True)).limit(200).all()
        candidates = []
        for card in catalog:
            attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
            if not attrs.get("combat_stats"):
                combat = build_combat_attrs(
                    card_code=card.code,
                    series=card.series or "",
                    position=attrs.get("position"),
                    overall_rating=attrs.get("overall_rating"),
                )
                attrs = {**attrs, **combat}
            cc = build_combat_card_from_virtual(
                {
                    "name": card.name,
                    "rarity": card.rarity,
                    "image_url": card.image_url,
                    "position": attrs.get("position"),
                    "star": 1,
                    "stats": attrs.get("combat_stats"),
                    "overall_rating": attrs.get("overall_rating"),
                    "team_id": card.team_id,
                    "card_code": card.code,
                },
                side="defender",
            )
            bp = battle_power(cc)
            if lo <= bp <= hi or not candidates:
                candidates.append(
                    {
                        "name": card.name,
                        "rarity": card.rarity,
                        "image_url": card.image_url,
                        "position": cc.position,
                        "star": 1,
                        "combat_stats": cc.stats,
                        "overall_rating": cc.overall_rating,
                        "team_id": card.team_id,
                        "card_code": card.code,
                        "bp": bp,
                    }
                )
        if len(candidates) < 3:
            for card in catalog:
                attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
                candidates.append(
                    {
                        "name": card.name,
                        "rarity": card.rarity or "rare",
                        "image_url": card.image_url,
                        "position": normalize_position(attrs.get("position")),
                        "star": 1,
                        "combat_stats": attrs.get("combat_stats") or {},
                        "overall_rating": attrs.get("overall_rating") or 75,
                        "team_id": card.team_id,
                        "card_code": card.code,
                        "bp": target_bp,
                    }
                )
                if len(candidates) >= 10:
                    break
        # 尽量覆盖不同位置
        by_pos: dict[str, list] = {}
        for c in candidates:
            by_pos.setdefault(c["position"], []).append(c)
        picked: list[dict] = []
        for pos in ("FWD", "MID", "DEF", "GK"):
            if pos in by_pos and by_pos[pos]:
                picked.append(random.choice(by_pos[pos]))
            if len(picked) >= 3:
                break
        while len(picked) < 3 and candidates:
            extra = random.choice(candidates)
            if extra not in picked:
                picked.append(extra)
        return picked[:3] if picked else candidates[:3]

    def _validate_cards(
        self,
        user: User,
        card_ids: list[int],
        *,
        expected_lock: str = "none",
        require_minted: bool = False,
    ) -> list[UserCollectibleCard]:
        if len(card_ids) != DUEL_CARD_COUNT:
            raise BadRequestError(f"请选择 {DUEL_CARD_COUNT} 张卡牌")
        ids = list(dict.fromkeys(card_ids))
        if len(ids) != DUEL_CARD_COUNT:
            raise BadRequestError("不可重复选择同一张卡")
        rows = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.id.in_(ids))
            .with_for_update()
            .all()
        )
        if len(rows) != DUEL_CARD_COUNT:
            raise BadRequestError("包含无效卡牌")
        staked = self._staked_card_ids(user.id)
        for row in rows:
            if (row.count or 1) > 1:
                raise BadRequestError("叠卡不可出战，请先拆分")
            lock = row.lock_state or "none"
            if lock != expected_lock:
                if expected_lock == "duel":
                    raise BadRequestError("挑战方卡牌未处于对决锁定状态")
                raise BadRequestError("锁定中的卡牌不可出战")
            if row.id in staked:
                raise BadRequestError("质押中的卡牌不可出战")
            if require_minted and (row.chain_status or "none") != "minted":
                raise BadRequestError("凭证战需使用已铸造的文昌链卡牌")
        return rows

    def _assert_cards_not_in_pending(self, card_ids: list[int]) -> None:
        used = self._pending_pvp_card_ids()
        overlap = used.intersection(card_ids)
        if overlap:
            raise BadRequestError("部分卡牌已在待应战对决中")

    def _resolve_defender(
        self, *, defender_id: int | None = None, invite_code: str | None = None
    ) -> User:
        if defender_id:
            user = self.db.get(User, defender_id)
        elif invite_code:
            code = invite_code.strip().upper()
            user = self.db.query(User).filter(User.invite_code == code).first()
        else:
            raise BadRequestError("请指定对手（用户 ID 或邀请码）")
        if not user or user.status != "active":
            raise NotFoundError("对手不存在")
        return user

    def _validate_stake(self, stake: int) -> None:
        if stake <= 0:
            return
        lo, hi = self.settings.card_duel_stake_min, self.settings.card_duel_stake_max
        if stake < lo or stake > hi:
            raise BadRequestError(f"入场费区间 {lo}-{hi} 可用积分")

    def duel_config(self) -> dict[str, Any]:
        tiers_raw = (self.settings.card_duel_stake_tiers or "0,20,50").split(",")
        stake_tiers = []
        tier_labels = {
            0: "休闲",
            20: "进阶",
            50: "排位",
        }
        for raw in tiers_raw:
            try:
                val = int(raw.strip())
            except ValueError:
                continue
            if val < 0 or val > self.settings.card_duel_stake_max:
                continue
            stake_tiers.append(
                {
                    "stake": val,
                    "label": tier_labels.get(val, f"{val}分场"),
                }
            )
        if not stake_tiers:
            stake_tiers = [{"stake": 0, "label": "休闲"}]
        return {
            "stake_min": self.settings.card_duel_stake_min,
            "stake_max": self.settings.card_duel_stake_max,
            "stake_tiers": stake_tiers,
            "fee_pct": self.settings.card_duel_fee_pct,
            "mode": self.settings.card_duel_mode,
            "win_battalion": self.settings.card_duel_win_battalion,
            "pending_expire_hours": self.settings.card_duel_pending_expire_hours,
            "max_pending_per_user": self.settings.card_duel_max_pending_per_user,
            "quick_match_enabled": self.settings.card_duel_quick_match_enabled,
            "match_window_sec": self.settings.card_duel_match_window_sec,
            "match_elo_window": self.settings.card_duel_match_elo_window,
            "chain_queue_enabled": True,
        }

    def challenge_user(
        self,
        user: User,
        card_ids: list[int],
        *,
        defender_id: int | None = None,
        invite_code: str | None = None,
        stake_points: int = 0,
    ) -> dict[str, Any]:
        """向其他用户发起对决邀请。"""
        self.asset.assert_real_name(user)
        stake = max(0, stake_points)
        self._validate_stake(stake)

        defender = self._resolve_defender(defender_id=defender_id, invite_code=invite_code)
        if defender.id == user.id:
            raise BadRequestError("不能挑战自己")

        max_pending = self.settings.card_duel_max_pending_per_user
        if self._count_user_pending_pvp(user.id, as_challenger=True) >= max_pending:
            raise BadRequestError(f"待应战挑战过多（上限 {max_pending}），请先取消或等待对手应战")

        self._assert_cards_not_in_pending(card_ids)

        user_locked = self._lock_user(user.id)
        if not user_locked:
            raise NotFoundError("用户不存在")
        if stake > 0 and (user_locked.redeem_points or 0) < stake:
            raise BadRequestError("可用积分不足")

        ch_rows = self._validate_cards(user_locked, card_ids, expected_lock="none")

        duel = CardDuel(
            challenger_id=user_locked.id,
            defender_id=defender.id,
            mode="pvp",
            status="pending",
            challenger_card_ids=card_ids,
            defender_card_ids=None,
            stake_points=stake,
        )
        self.db.add(duel)
        self.db.flush()

        self._apply_duel_locks(ch_rows)

        if stake > 0:
            self.wallet.deduct_redeem_points(
                user_locked, stake, "duel_stake_escrow", "card_duel", duel.id
            )

        self.db.commit()
        return {
            "ok": True,
            "duel_id": duel.id,
            "defender_nickname": defender.nickname,
            "stake_points": stake,
            "notice": f"已向 {defender.nickname} 发起对决，等待应战",
        }

    def pending_duels(self, user: User) -> list[dict[str, Any]]:
        """待应战列表（我是防守方）。"""
        rows = (
            self.db.query(CardDuel, User)
            .join(User, CardDuel.challenger_id == User.id)
            .filter(
                CardDuel.defender_id == user.id,
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
            )
            .order_by(CardDuel.id.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "duel_id": d.id,
                "challenger_id": d.challenger_id,
                "challenger_nickname": u.nickname,
                "stake_points": d.stake_points or 0,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d, u in rows
        ]

    def accept_duel(self, user: User, duel_id: int, card_ids: list[int]) -> dict[str, Any]:
        """应战并完成对决。"""
        self.asset.assert_real_name(user)
        duel = (
            self.db.query(CardDuel)
            .filter(CardDuel.id == duel_id, CardDuel.status == "pending", CardDuel.mode == "pvp")
            .with_for_update()
            .first()
        )
        if not duel or duel.defender_id != user.id:
            raise NotFoundError("对决不存在或已失效")
        if duel.status != "pending":
            raise BadRequestError("对决已结束")

        stake = duel.stake_points or 0
        self._validate_stake(stake)

        users = self._lock_users_ordered(user.id, duel.challenger_id)
        defender_locked = users[user.id]
        challenger_locked = users[duel.challenger_id]

        if stake > 0 and (defender_locked.redeem_points or 0) < stake:
            raise BadRequestError("可用积分不足")

        self._validate_cards(challenger_locked, duel.challenger_card_ids or [], expected_lock="duel")
        df_rows = self._validate_cards(defender_locked, card_ids, expected_lock="none")
        self._apply_duel_locks(df_rows)

        duel.defender_card_ids = card_ids
        if stake > 0:
            self.wallet.deduct_redeem_points(
                defender_locked, stake, "duel_stake_escrow", "card_duel", duel.id
            )

        try:
            return self._settle_duel(
                duel, challenger_locked, defender=defender_locked, acting_user=defender_locked
            )
        except Exception:
            self._release_duel_locks(card_ids)
            raise

    def cancel_duel(self, user: User, duel_id: int) -> dict[str, Any]:
        """挑战方取消待应战 PVP，退还 escrow 并解锁卡牌。"""
        duel = (
            self.db.query(CardDuel)
            .filter(
                CardDuel.id == duel_id,
                CardDuel.challenger_id == user.id,
                CardDuel.mode == "pvp",
            )
            .with_for_update()
            .first()
        )
        if not duel:
            raise NotFoundError("对决不存在")
        if duel.status != "pending":
            raise BadRequestError("只能取消待应战的对决")

        challenger = self._lock_user(user.id)
        if not challenger:
            raise NotFoundError("用户不存在")

        self._refund_challenger_stake(duel, challenger)
        self._release_duel_locks(duel.challenger_card_ids or [])
        duel.status = "cancelled"
        duel.settled_at = _utcnow()
        self.db.commit()
        return {"ok": True, "duel_id": duel.id, "notice": "已取消挑战，入场费已退还"}

    def expire_pending_pvp_duels(self) -> dict[str, int]:
        """Scheduler：过期未应战的 PVP 自动取消并退款。"""
        cutoff = _utcnow() - timedelta(hours=self.settings.card_duel_pending_expire_hours)
        rows = (
            self.db.query(CardDuel)
            .filter(
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
                CardDuel.created_at.isnot(None),
                CardDuel.created_at < cutoff,
            )
            .with_for_update()
            .all()
        )
        expired = 0
        for duel in rows:
            try:
                challenger = self._lock_user(duel.challenger_id)
                if challenger:
                    self._refund_challenger_stake(duel, challenger)
                self._release_duel_locks(duel.challenger_card_ids or [])
                duel.status = "expired"
                duel.settled_at = _utcnow()
                expired += 1
            except Exception:
                logger.exception("expire pending duel failed id=%s", duel.id)
        if expired:
            self.db.commit()
        return {"expired": expired}

    def outgoing_duels(self, user: User) -> list[dict[str, Any]]:
        """我发起的待应战挑战。"""
        rows = (
            self.db.query(CardDuel, User)
            .join(User, CardDuel.defender_id == User.id)
            .filter(
                CardDuel.challenger_id == user.id,
                CardDuel.status == "pending",
                CardDuel.mode == "pvp",
            )
            .order_by(CardDuel.id.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "duel_id": d.id,
                "defender_nickname": u.nickname if u else "—",
                "stake_points": d.stake_points or 0,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d, u in rows
        ]

    def _resolve_best_of_3(self, duel: CardDuel) -> tuple[int, int, str, dict[str, Any]]:
        c_cards = self._load_side_combat_cards(duel, "challenger")
        d_cards = self._load_side_combat_cards(duel, "defender")
        result = resolve_duel(c_cards, d_cards, mode="best_of_3", bp_rng_pct=self.settings.card_duel_bp_rng_pct)
        c_wins = result["challenger_round_wins"]
        d_wins = result["defender_round_wins"]
        for rnd_data in result["rounds"]:
            self.db.add(
                CardDuelLog(
                    duel_id=duel.id,
                    round_no=rnd_data["round"],
                    challenger_power=int(rnd_data["challenger_score"]),
                    defender_power=int(rnd_data["defender_score"]),
                    winner_side=rnd_data["winner_side"],
                    result_json=rnd_data,
                )
            )
        winner = duel.challenger_id if c_wins >= d_wins else (duel.defender_id or 0)
        return c_wins, d_wins, "challenger" if winner == duel.challenger_id else "defender", result

    def _load_side_combat_cards(self, duel: CardDuel, side: str) -> list:
        if side == "challenger":
            ids = duel.challenger_card_ids or []
            uid = duel.challenger_id
        else:
            ids = duel.defender_card_ids or []
            uid = duel.defender_id
        if duel.mode == "ai" and side == "defender":
            deck = duel.ai_deck_json or []
            return [build_combat_card_from_virtual(v, side="defender") for v in deck]
        if not uid:
            return []
        return self._load_user_combat_cards(ids, uid, side=side)

    def _resolve_total_power(self, duel: CardDuel) -> tuple[int, int, str, dict[str, Any]]:
        c_cards = self._load_side_combat_cards(duel, "challenger")
        d_cards = self._load_side_combat_cards(duel, "defender")
        result = resolve_duel(c_cards, d_cards, mode="total_power", bp_rng_pct=self.settings.card_duel_bp_rng_pct)
        rnd = result["rounds"][0]
        self.db.add(
            CardDuelLog(
                duel_id=duel.id,
                round_no=1,
                challenger_power=int(rnd["challenger_score"]),
                defender_power=int(rnd["defender_score"]),
                winner_side=rnd["winner_side"],
                result_json=rnd,
            )
        )
        cp = int(rnd["challenger_score"])
        dp = int(rnd["defender_score"])
        winner = duel.challenger_id if cp >= dp else (duel.defender_id or 0)
        return cp, dp, "challenger" if winner == duel.challenger_id else "defender", result

    def challenge_ai(
        self, user: User, card_ids: list[int], *, stake_points: int = 0
    ) -> dict[str, Any]:
        self.asset.assert_real_name(user)
        stake = max(0, stake_points)
        self._validate_stake(stake)

        user_locked = self._lock_user(user.id)
        if not user_locked:
            raise NotFoundError("用户不存在")
        if stake > 0 and (user_locked.redeem_points or 0) < stake:
            raise BadRequestError("可用积分不足")

        ch_rows = self._validate_cards(user_locked, card_ids)
        ai_deck = self._generate_ai_deck(ch_rows)

        duel = CardDuel(
            challenger_id=user_locked.id,
            defender_id=None,
            mode="ai",
            status="pending",
            challenger_card_ids=card_ids,
            defender_card_ids=[0, 0, 0],
            ai_deck_json=ai_deck,
            stake_points=stake,
        )
        self.db.add(duel)
        self.db.flush()

        if stake > 0:
            self.wallet.deduct_redeem_points(
                user_locked, stake, "duel_stake_escrow", "card_duel", duel.id
            )

        return self._settle_duel(duel, user_locked, acting_user=user_locked)

    def _settle_duel(
        self,
        duel: CardDuel,
        challenger: User,
        *,
        defender: User | None = None,
        acting_user: User | None = None,
    ) -> dict[str, Any]:
        if duel.status == "settled":
            raise BadRequestError("对决已结算")

        replay: dict[str, Any]
        if self.settings.card_duel_mode == "total_power":
            cp, dp, _, replay = self._resolve_total_power(duel)
            duel.challenger_power = cp
            duel.defender_power = dp
            winner_id = duel.challenger_id if cp >= dp else duel.defender_id
        else:
            c_wins, d_wins, _, replay = self._resolve_best_of_3(duel)
            duel.challenger_power = c_wins
            duel.defender_power = d_wins
            winner_id = duel.challenger_id if c_wins >= d_wins else duel.defender_id

        duel.replay_json = replay

        duel.winner_id = winner_id
        duel.status = "settled"
        duel.settled_at = _utcnow()

        stake = duel.stake_points or 0
        payout_notice = ""
        winner_user = challenger if winner_id == duel.challenger_id else defender
        loser_user = defender if winner_id == duel.challenger_id else challenger
        fee = 0
        if stake > 0 and winner_user:
            # PVP：双方 escrow；AI：仅挑战者单份奖池（禁止凭空增发积分）
            pot = stake * 2 if duel.mode == "pvp" else stake
            fee = int(round(pot * self.settings.card_duel_fee_pct))
            gain = max(0, pot - fee)
            self.wallet.add_redeem_points(
                winner_user, gain, "duel_win", "card_duel", duel.id
            )
            payout_notice = f"赢得 {gain} 可用积分"
            if fee > 0:
                self._record_duel_fee_sink(fee, duel.id)
        elif stake > 0:
            payout_notice = "本次未获胜，入场费已扣除"

        collectible_drop: dict[str, Any] | None = None
        battalion_added = 0
        if winner_user:
            try:
                collectible_drop = self._award_duel_win_drops(winner_user, duel)
            except Exception:
                logger.exception("duel win drop failed")
            try:
                from app.services.arena_service import ArenaService

                battalion_added = ArenaService(self.db).apply_duel_win_reward(
                    winner_user, duel.id
                )
            except Exception:
                logger.exception("duel battalion reward failed")
        elif loser_user:
            try:
                self._award_duel_loss_comfort(loser_user, duel.id)
            except Exception:
                logger.exception("duel loss comfort failed")

        ch_elo_delta = def_elo_delta = 0
        try:
            ch_elo_delta, def_elo_delta = self._apply_duel_elo(
                duel, challenger, defender, winner_id
            )
        except Exception:
            logger.exception("duel elo apply failed")

        if collectible_drop and isinstance(replay, dict):
            replay["collectible_drop"] = collectible_drop
            duel.replay_json = replay

        try:
            from app.services.duel_season_service import DuelSeasonService

            DuelSeasonService(self.db).record_duel_result(
                challenger, defender, winner_id=winner_id or 0, duel_id=duel.id
            )
        except Exception:
            logger.exception("duel season record failed")

        all_card_ids = list(duel.challenger_card_ids or []) + list(duel.defender_card_ids or [])
        self._release_duel_locks(all_card_ids)

        self.db.commit()
        viewer = acting_user or challenger
        won = winner_id == viewer.id
        viewer_elo_delta = (
            ch_elo_delta if viewer.id == duel.challenger_id else def_elo_delta
        )
        if viewer.id == duel.challenger_id:
            viewer_elo = int(challenger.duel_elo or 1000)
        elif defender and viewer.id == defender.id:
            viewer_elo = int(defender.duel_elo or 1000)
        else:
            viewer_elo = int(getattr(viewer, "duel_elo", None) or 1000)
        result = {
            "ok": True,
            "duel_id": duel.id,
            "won": won,
            "winner_id": winner_id,
            "challenger_power": duel.challenger_power,
            "defender_power": duel.defender_power,
            "stake_points": stake,
            "payout_notice": payout_notice,
            "battalion_added": battalion_added,
            "elo_delta": viewer_elo_delta,
            "duel_elo": viewer_elo,
            "notice": "对决胜利！" if won else "对决失败，再接再厉",
            "rounds": replay.get("rounds", []),
            "replay": replay,
            "collectible_drop": collectible_drop,
        }
        try:
            from app.core.user_ws_hub import push_user_event

            ws_payload = {
                "type": "duel_settled",
                "duel_id": duel.id,
                "won": won,
                "elo_delta": viewer_elo_delta,
                "duel_elo": viewer_elo,
            }
            push_user_event(viewer.id, ws_payload)
            if duel.mode == "pvp" and defender and defender.id != viewer.id:
                other_delta = def_elo_delta if viewer.id == duel.challenger_id else ch_elo_delta
                push_user_event(
                    defender.id if viewer.id == duel.challenger_id else challenger.id,
                    {
                        **ws_payload,
                        "won": winner_id
                        == (defender.id if viewer.id == duel.challenger_id else challenger.id),
                        "elo_delta": other_delta,
                        "duel_elo": int(
                            (defender if viewer.id == duel.challenger_id else challenger).duel_elo
                            or 1000
                        ),
                    },
                )
        except Exception:
            logger.debug("duel_settled ws push skipped")
        return result

    def get_duel_detail(self, user: User, duel_id: int) -> dict[str, Any]:
        duel = self.db.get(CardDuel, duel_id)
        if not duel:
            raise NotFoundError("对决不存在")
        if user.id not in (duel.challenger_id, duel.defender_id or -1):
            raise NotFoundError("无权查看该对决")
        logs = (
            self.db.query(CardDuelLog)
            .filter(CardDuelLog.duel_id == duel.id)
            .order_by(CardDuelLog.round_no.asc())
            .all()
        )
        rounds = [log.result_json for log in logs if log.result_json]
        if not rounds and duel.replay_json:
            rounds = duel.replay_json.get("rounds", [])
        nick_map = {}
        for uid in filter(None, [duel.challenger_id, duel.defender_id, duel.winner_id]):
            u = self.db.get(User, uid)
            if u:
                nick_map[uid] = u.nickname
        is_challenger = duel.challenger_id == user.id
        user_won = duel.winner_id == user.id if duel.status == "settled" else False
        return {
            "duel_id": duel.id,
            "mode": duel.mode,
            "status": duel.status,
            "won": duel.winner_id == user.id if duel.status == "settled" else None,
            "role": "challenger" if is_challenger else "defender",
            "challenger_nickname": nick_map.get(duel.challenger_id, "—"),
            "defender_nickname": nick_map.get(duel.defender_id, "AI 教练") if duel.mode == "ai" else nick_map.get(duel.defender_id, "—"),
            "challenger_power": duel.challenger_power,
            "defender_power": duel.defender_power,
            "winner_id": duel.winner_id,
            "stake_points": duel.stake_points,
            "rounds": rounds,
            "replay": duel.replay_json,
            "ai_deck": duel.ai_deck_json if duel.mode == "ai" else None,
            "settled_at": duel.settled_at.isoformat() if duel.settled_at else None,
            "challenger_elo_delta": duel.challenger_elo_delta if duel.status == "settled" else None,
            "defender_elo_delta": duel.defender_elo_delta if duel.status == "settled" else None,
            "your_elo_delta": (
                duel.challenger_elo_delta if is_challenger else duel.defender_elo_delta
            )
            if duel.status == "settled"
            else None,
            "collectible_drop": (
                (duel.replay_json or {}).get("collectible_drop")
                if duel.status == "settled" and user_won
                else None
            ),
        }

    def history(self, user: User, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            self.db.query(CardDuel)
            .filter(
                (CardDuel.challenger_id == user.id) | (CardDuel.defender_id == user.id),
                CardDuel.status == "settled",
            )
            .order_by(CardDuel.id.desc())
            .limit(min(limit, 50))
            .all()
        )
        user_ids = set()
        for d in rows:
            if d.challenger_id:
                user_ids.add(d.challenger_id)
            if d.defender_id:
                user_ids.add(d.defender_id)
        nick_map = {}
        if user_ids:
            for u in self.db.query(User).filter(User.id.in_(user_ids)).all():
                nick_map[u.id] = u.nickname

        out = []
        for d in rows:
            is_challenger = d.challenger_id == user.id
            opp_id = d.defender_id if is_challenger else d.challenger_id
            out.append(
                {
                    "duel_id": d.id,
                    "mode": d.mode,
                    "won": d.winner_id == user.id,
                    "role": "challenger" if is_challenger else "defender",
                    "opponent_nickname": nick_map.get(opp_id, "AI") if d.mode == "ai" else nick_map.get(opp_id, "—"),
                    "challenger_power": d.challenger_power,
                    "defender_power": d.defender_power,
                    "stake_points": d.stake_points,
                    "elo_delta": (
                        d.challenger_elo_delta if is_challenger else d.defender_elo_delta
                    ),
                    "at": d.settled_at.isoformat() if d.settled_at else None,
                }
            )
        return out

    def deck_preview(self, user: User, card_ids: list[int]) -> dict[str, Any]:
        if len(card_ids) != DUEL_CARD_COUNT:
            raise BadRequestError(f"请选择 {DUEL_CARD_COUNT} 张卡牌")
        rows = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.id.in_(card_ids))
            .all()
        )
        if len(rows) != DUEL_CARD_COUNT:
            raise BadRequestError("包含无效卡牌")
        cards = []
        for cid in card_ids:
            row = next((r for r in rows if r.id == cid), None)
            if not row:
                continue
            card = self.db.get(CollectibleCard, row.card_id)
            if card:
                cards.append(build_combat_card_from_row(row, card))
        summary = deck_summary(cards)
        hints = []
        positions = summary.get("positions") or []
        if len(positions) >= 2:
            from app.services.combat_engine import MATCHUP_HINTS

            for i in range(min(3, len(positions))):
                for mh in MATCHUP_HINTS:
                    if positions[i] == mh["att"]:
                        hints.append(f"第{i + 1}局（{positions[i]}）: {mh['hint']}")
                        break
        summary["matchup_hints"] = hints[:3]
        return summary

    def _duel_participant_subquery(self):
        ch = self.db.query(CardDuel.challenger_id.label("uid")).filter(
            CardDuel.status == "settled"
        )
        df = self.db.query(CardDuel.defender_id.label("uid")).filter(
            CardDuel.status == "settled",
            CardDuel.defender_id.isnot(None),
        )
        return ch.union(df).subquery()

    def duel_quick_summary(self, user: User) -> dict[str, int]:
        from sqlalchemy import or_

        uid = user.id
        base = self.db.query(CardDuel).filter(
            CardDuel.status == "settled",
            or_(CardDuel.challenger_id == uid, CardDuel.defender_id == uid),
        )
        total = base.count()
        wins = base.filter(CardDuel.winner_id == uid).count()
        return {"total_duels": total, "wins": wins, "losses": max(0, total - wins)}

    def duel_elo_rank(self, user_id: int) -> int | None:
        from sqlalchemy import func

        sub = self._duel_participant_subquery()
        user = self.db.get(User, user_id)
        if not user:
            return None
        elo = int(user.duel_elo or 1000)
        higher = (
            self.db.query(func.count(User.id))
            .join(sub, User.id == sub.c.uid)
            .filter(User.duel_elo > elo)
            .scalar()
            or 0
        )
        return int(higher) + 1

    def duel_wins_rank(self, user_id: int) -> int | None:
        from sqlalchemy import func

        sub = (
            self.db.query(
                CardDuel.winner_id.label("uid"),
                func.count(CardDuel.id).label("wins"),
            )
            .filter(CardDuel.status == "settled", CardDuel.winner_id.isnot(None))
            .group_by(CardDuel.winner_id)
            .subquery()
        )
        row = (
            self.db.query(sub.c.uid, sub.c.wins)
            .filter(sub.c.uid == user_id)
            .first()
        )
        if not row:
            return None
        higher = (
            self.db.query(func.count())
            .select_from(sub)
            .filter(sub.c.wins > row.wins)
            .scalar()
            or 0
        )
        return int(higher) + 1

    def duel_stats(self, user: User) -> dict[str, Any]:
        rows = (
            self.db.query(CardDuel)
            .filter(
                (CardDuel.challenger_id == user.id) | (CardDuel.defender_id == user.id),
                CardDuel.status == "settled",
            )
            .order_by(CardDuel.id.desc())
            .limit(50)
            .all()
        )
        wins = losses = 0
        streak = 0
        streak_type: str | None = None
        for d in rows:
            won = d.winner_id == user.id
            if wins + losses == 0:
                streak = 1
                streak_type = "win" if won else "lose"
            elif (won and streak_type == "win") or (not won and streak_type == "lose"):
                streak += 1
            else:
                break
            if won:
                wins += 1
            else:
                losses += 1
        total = wins + losses
        ai_wins = sum(1 for d in rows if d.winner_id == user.id and d.mode == "ai")
        pvp_wins = sum(1 for d in rows if d.winner_id == user.id and d.mode == "pvp")
        from app.services.duel_elo_service import DEFAULT_ELO, elo_tier

        duel_elo = int(getattr(user, "duel_elo", None) or DEFAULT_ELO)
        return {
            "total_duels": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "current_streak": streak,
            "streak_type": streak_type,
            "ai_wins": ai_wins,
            "pvp_wins": pvp_wins,
            "duel_elo": duel_elo,
            "elo_tier": elo_tier(duel_elo),
            "rank_tier": self._duel_rank_tier(wins, total),
        }

    def duel_leaderboard(self, limit: int = 20, *, by: str = "wins") -> list[dict[str, Any]]:
        from app.services.duel_elo_service import elo_tier

        if by == "elo":
            sub = self._duel_participant_subquery()
            rows = (
                self.db.query(User.id, User.nickname, User.duel_elo)
                .join(sub, User.id == sub.c.uid)
                .order_by(User.duel_elo.desc(), User.id.asc())
                .limit(min(limit, 50))
                .all()
            )
            return [
                {
                    "user_id": r.id,
                    "nickname": r.nickname,
                    "duel_elo": int(r.duel_elo or 1000),
                    "elo_tier": elo_tier(int(r.duel_elo or 1000)),
                }
                for r in rows
            ]

        from sqlalchemy import func

        sub = (
            self.db.query(
                CardDuel.winner_id.label("uid"),
                func.count(CardDuel.id).label("wins"),
            )
            .filter(CardDuel.status == "settled", CardDuel.winner_id.isnot(None))
            .group_by(CardDuel.winner_id)
            .subquery()
        )
        rows = (
            self.db.query(User.id, User.nickname, User.duel_elo, sub.c.wins)
            .join(sub, User.id == sub.c.uid)
            .order_by(sub.c.wins.desc())
            .limit(min(limit, 50))
            .all()
        )
        return [
            {
                "user_id": r.id,
                "nickname": r.nickname,
                "wins": int(r.wins),
                "duel_elo": int(r.duel_elo or 1000),
            }
            for r in rows
        ]

    def recommend_deck(self, user: User) -> dict[str, Any]:
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user.id)
            .all()
        )
        staked_ids = self._staked_card_ids(user.id)
        cards = []
        for row, card in rows:
            if (row.count or 1) > 1:
                continue
            if row.lock_state and row.lock_state != "none":
                continue
            if row.id in staked_ids:
                continue
            cards.append(build_combat_card_from_row(row, card))
        if len(cards) < DUEL_CARD_COUNT:
            raise BadRequestError(f"可用卡牌不足 {DUEL_CARD_COUNT} 张，无法智能组牌")
        from app.services.duel_elo_service import recommend_deck_from_cards

        result = recommend_deck_from_cards(cards)
        by_id = {c.user_card_id: c for c in cards if c.user_card_id}
        result["cards"] = [
            {
                "user_card_id": cid,
                "name": by_id[cid].name if cid in by_id else "—",
                "position": by_id[cid].position,
                "bp": battle_power(by_id[cid]) if cid in by_id else 0,
            }
            for cid in result.get("card_ids") or []
        ]
        return result

    def _duel_rank_tier(self, wins: int, total: int) -> dict[str, str]:
        if total < 3:
            return {"code": "rookie", "label": "新秀"}
        rate = wins / total if total else 0
        if wins >= 30 and rate >= 0.6:
            return {"code": "master", "label": "对决大师"}
        if wins >= 15 and rate >= 0.55:
            return {"code": "veteran", "label": "老将"}
        if wins >= 5:
            return {"code": "regular", "label": "常客"}
        return {"code": "rookie", "label": "新秀"}
