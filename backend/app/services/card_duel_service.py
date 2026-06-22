"""卡牌对决 PVP — 异步选卡比战力（可用积分入场）。"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.data.asset_catalog import estimate_card_value
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

    def eligible_cards(self, user: User) -> list[dict[str, Any]]:
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
                    "power": power,
                }
            )
        return sorted(out, key=lambda x: -x["power"])

    def _card_power(self, row: UserCollectibleCard, card: CollectibleCard) -> int:
        attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
        rating = int(attrs.get("overall_rating") or 0)
        base = estimate_card_value(card.rarity, row.star, serial_no=row.serial_no, mint_total=row.mint_total)
        return base + rating * 2

    def _validate_cards(
        self,
        user: User,
        card_ids: list[int],
        *,
        expected_lock: str = "none",
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
        return {
            "stake_min": self.settings.card_duel_stake_min,
            "stake_max": self.settings.card_duel_stake_max,
            "fee_pct": self.settings.card_duel_fee_pct,
            "mode": self.settings.card_duel_mode,
            "win_battalion": self.settings.card_duel_win_battalion,
            "pending_expire_hours": self.settings.card_duel_pending_expire_hours,
            "max_pending_per_user": self.settings.card_duel_max_pending_per_user,
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

    def _ai_pick_cards(self) -> list[int]:
        return [0, 0, 0]

    def _total_power(self, card_ids: list[int], user_id: int | None = None) -> int:
        if not card_ids or card_ids == [0, 0, 0]:
            return random.randint(200, 450)
        q = (
            self.db.query(UserCollectibleCard, CollectibleCard)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .filter(UserCollectibleCard.id.in_(card_ids))
        )
        if user_id:
            q = q.filter(UserCollectibleCard.user_id == user_id)
        total = 0
        for row, card in q.all():
            total += self._card_power(row, card)
        return total

    def _resolve_best_of_3(self, duel: CardDuel) -> tuple[int, int, str]:
        c_ids = duel.challenger_card_ids or []
        d_ids = duel.defender_card_ids or []
        c_wins = d_wins = 0
        for rnd in range(1, 4):
            cp = self._card_power_for_slot(c_ids, rnd - 1, duel.challenger_id)
            dp = self._card_power_for_slot(d_ids, rnd - 1, duel.defender_id)
            side = "challenger" if cp >= dp else "defender"
            if side == "challenger":
                c_wins += 1
            else:
                d_wins += 1
            self.db.add(
                CardDuelLog(
                    duel_id=duel.id,
                    round_no=rnd,
                    challenger_power=cp,
                    defender_power=dp,
                    winner_side=side,
                )
            )
        winner = duel.challenger_id if c_wins >= d_wins else (duel.defender_id or 0)
        return c_wins, d_wins, "challenger" if winner == duel.challenger_id else "defender"

    def _card_power_for_slot(self, card_ids: list[int], idx: int, user_id: int | None) -> int:
        if idx >= len(card_ids) or not card_ids[idx]:
            return random.randint(60, 150)
        row = self.db.get(UserCollectibleCard, card_ids[idx])
        if not row:
            return random.randint(60, 150)
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            return random.randint(60, 150)
        return self._card_power(row, card)

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

        self._validate_cards(user_locked, card_ids)
        ai_cards = self._ai_pick_cards()

        duel = CardDuel(
            challenger_id=user_locked.id,
            defender_id=None,
            mode="ai",
            status="pending",
            challenger_card_ids=card_ids,
            defender_card_ids=ai_cards,
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

        if self.settings.card_duel_mode == "total_power":
            cp = self._total_power(duel.challenger_card_ids, duel.challenger_id)
            dp = self._total_power(duel.defender_card_ids or [], duel.defender_id)
            duel.challenger_power = cp
            duel.defender_power = dp
            winner_id = duel.challenger_id if cp >= dp else duel.defender_id
            self.db.add(
                CardDuelLog(
                    duel_id=duel.id,
                    round_no=1,
                    challenger_power=cp,
                    defender_power=dp,
                    winner_side="challenger" if winner_id == duel.challenger_id else "defender",
                )
            )
        else:
            c_wins, d_wins, _ = self._resolve_best_of_3(duel)
            duel.challenger_power = c_wins
            duel.defender_power = d_wins
            winner_id = duel.challenger_id if c_wins >= d_wins else duel.defender_id

        duel.winner_id = winner_id
        duel.status = "settled"
        duel.settled_at = _utcnow()

        stake = duel.stake_points or 0
        payout_notice = ""
        winner_user = challenger if winner_id == duel.challenger_id else defender
        if stake > 0 and winner_user:
            # PVP：双方 escrow；AI：仅挑战者单份奖池（禁止凭空增发积分）
            pot = stake * 2 if duel.mode == "pvp" else stake
            fee = int(round(pot * self.settings.card_duel_fee_pct))
            gain = max(0, pot - fee)
            self.wallet.add_redeem_points(
                winner_user, gain, "duel_win", "card_duel", duel.id
            )
            payout_notice = f"赢得 {gain} 可用积分"
        elif stake > 0:
            payout_notice = "本次未获胜，入场费已扣除"

        battalion_added = 0
        if winner_user:
            try:
                from app.services.arena_service import ArenaService

                battalion_added = ArenaService(self.db).apply_duel_win_reward(
                    winner_user, duel.id
                )
            except Exception:
                logger.exception("duel battalion reward failed")

        all_card_ids = list(duel.challenger_card_ids or []) + list(duel.defender_card_ids or [])
        self._release_duel_locks(all_card_ids)

        self.db.commit()
        viewer = acting_user or challenger
        won = winner_id == viewer.id
        return {
            "ok": True,
            "duel_id": duel.id,
            "won": won,
            "winner_id": winner_id,
            "challenger_power": duel.challenger_power,
            "defender_power": duel.defender_power,
            "stake_points": stake,
            "payout_notice": payout_notice,
            "battalion_added": battalion_added,
            "notice": "对决胜利！" if won else "对决失败，再接再厉",
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
                    "at": d.settled_at.isoformat() if d.settled_at else None,
                }
            )
        return out
