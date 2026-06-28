"""卡牌对决快速匹配。"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import CardDuelMatchQueue, User
from app.services.card_duel_service import CardDuelService, DUEL_CARD_COUNT

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CardDuelMatchService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.duel_svc = CardDuelService(db)

    def _active_queue(self, user_id: int) -> CardDuelMatchQueue | None:
        return (
            self.db.query(CardDuelMatchQueue)
            .filter(
                CardDuelMatchQueue.user_id == user_id,
                CardDuelMatchQueue.status.in_(("waiting", "matched")),
            )
            .order_by(CardDuelMatchQueue.id.desc())
            .first()
        )

    def enter_queue(
        self,
        user: User,
        card_ids: list[int],
        stake_points: int = 0,
        *,
        match_mode: str = "casual",
    ) -> dict[str, Any]:
        if not self.settings.card_duel_quick_match_enabled:
            raise BadRequestError("快速匹配暂未开放")
        self.duel_svc.asset.assert_real_name(user)
        stake = max(0, stake_points)
        self.duel_svc._validate_stake(stake)

        existing = self._active_queue(user.id)
        if existing and existing.status == "waiting":
            raise BadRequestError("你已在匹配队列中")

        mode = (match_mode or "casual").lower()
        if mode not in ("casual", "ranked", "chain"):
            raise BadRequestError("无效匹配模式")
        require_minted = mode == "chain"

        user_locked = self.duel_svc._lock_user(user.id)
        if not user_locked:
            raise NotFoundError("用户不存在")
        if stake > 0 and (user_locked.redeem_points or 0) < stake:
            raise BadRequestError("可用积分不足")

        rows = self.duel_svc._validate_cards(
            user_locked, card_ids, require_minted=require_minted
        )
        self.duel_svc._apply_duel_locks(rows)
        deck_bp = int(self.duel_svc._deck_average_bp(rows))
        tier = self.duel_svc._bp_tier(deck_bp)
        window = self.settings.card_duel_match_window_sec

        entry = CardDuelMatchQueue(
            user_id=user.id,
            card_ids=card_ids,
            deck_bp=deck_bp,
            stake_points=stake,
            tier=tier,
            match_mode=mode,
            status="waiting",
            expires_at=_utcnow() + timedelta(seconds=window),
        )
        self.db.add(entry)
        self.db.commit()
        mode_notice = {
            "casual": "休闲匹配",
            "ranked": "排位匹配",
            "chain": "文昌链凭证战",
        }.get(mode, "匹配")
        return {
            "ok": True,
            "queue_id": entry.id,
            "deck_bp": deck_bp,
            "tier": tier,
            "match_mode": mode,
            "expires_at": entry.expires_at.isoformat(),
            "notice": f"已进入{mode_notice}队列，正在寻找对手…",
        }

    def cancel_queue(self, user: User) -> dict[str, Any]:
        entry = (
            self.db.query(CardDuelMatchQueue)
            .filter(
                CardDuelMatchQueue.user_id == user.id,
                CardDuelMatchQueue.status == "waiting",
            )
            .with_for_update()
            .first()
        )
        if not entry:
            raise NotFoundError("未在匹配队列中")
        self.duel_svc._release_duel_locks(list(entry.card_ids or []))
        entry.status = "cancelled"
        self.db.commit()
        return {"ok": True, "notice": "已取消匹配"}

    def queue_status(self, user: User) -> dict[str, Any]:
        entry = self._active_queue(user.id)
        if not entry:
            return {"in_queue": False}
    return {
            "in_queue": entry.status == "waiting",
            "matched": entry.status == "matched",
            "queue_id": entry.id,
            "deck_bp": entry.deck_bp,
            "tier": entry.tier,
            "stake_points": entry.stake_points,
            "match_mode": getattr(entry, "match_mode", "casual"),
            "duel_id": entry.duel_id,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }

    def process_matchmaking(self) -> dict[str, int]:
        """Ingest job: 配对 waiting 队列。"""
        now = _utcnow()
        expired = (
            self.db.query(CardDuelMatchQueue)
            .filter(CardDuelMatchQueue.status == "waiting", CardDuelMatchQueue.expires_at < now)
            .with_for_update()
            .all()
        )
        exp_count = 0
        for entry in expired:
            self.duel_svc._release_duel_locks(list(entry.card_ids or []))
            entry.status = "expired"
            exp_count += 1

        waiting = (
            self.db.query(CardDuelMatchQueue)
            .filter(CardDuelMatchQueue.status == "waiting", CardDuelMatchQueue.expires_at >= now)
            .order_by(CardDuelMatchQueue.created_at.asc())
            .all()
        )
        matched = 0
        used_ids: set[int] = set()
        elo_window = self.settings.card_duel_match_elo_window
        user_elo: dict[int, int] = {}
        for entry in waiting:
            if entry.user_id not in user_elo:
                u = self.db.get(User, entry.user_id)
                user_elo[entry.user_id] = int(getattr(u, "duel_elo", None) or 1000)

        for i, a in enumerate(waiting):
            if a.id in used_ids:
                continue
            for b in waiting[i + 1 :]:
                if b.id in used_ids:
                    continue
                if a.user_id == b.user_id:
                    continue
                if a.stake_points != b.stake_points:
                    continue
                mode_a = getattr(a, "match_mode", "casual") or "casual"
                mode_b = getattr(b, "match_mode", "casual") or "casual"
                if mode_a != mode_b:
                    continue
                if abs(a.tier - b.tier) > 1:
                    continue
                elo_a = user_elo.get(a.user_id, 1000)
                elo_b = user_elo.get(b.user_id, 1000)
                if abs(elo_a - elo_b) > elo_window:
                    continue
                bp_a, bp_b = a.deck_bp or 0, b.deck_bp or 0
                if bp_a and bp_b:
                    diff_pct = abs(bp_a - bp_b) / max(bp_a, bp_b)
                    if diff_pct > 0.15:
                        continue
                try:
                    self._create_matched_duel(a, b)
                    used_ids.add(a.id)
                    used_ids.add(b.id)
                    matched += 1
                    break
                except Exception:
                    logger.exception("match pair failed %s %s", a.id, b.id)

        if exp_count or matched:
            self.db.commit()
        return {"expired": exp_count, "matched": matched}

    def _create_matched_duel(self, qa: CardDuelMatchQueue, qb: CardDuelMatchQueue) -> None:
        challenger_entry, defender_entry = (qa, qb) if random.random() < 0.5 else (qb, qa)
        self.duel_svc._release_duel_locks(list(challenger_entry.card_ids or []))
        self.duel_svc._release_duel_locks(list(defender_entry.card_ids or []))
        challenger = self.db.get(User, challenger_entry.user_id)
        defender = self.db.get(User, defender_entry.user_id)
        if not challenger or not defender:
            raise BadRequestError("用户无效")

        stake = challenger_entry.stake_points or 0
        invite = self.duel_svc.challenge_user(
            challenger,
            list(challenger_entry.card_ids),
            defender_id=defender.id,
            stake_points=stake,
        )
        duel_id = invite["duel_id"]
        result = self.duel_svc.accept_duel(defender, duel_id, list(defender_entry.card_ids))

        for entry, other in ((qa, qb), (qb, qa)):
            entry.status = "matched"
            entry.duel_id = duel_id
            entry.matched_user_id = other.user_id

        try:
            from app.core.user_ws_hub import push_user_event

            payload = {"type": "duel_matched", "duel_id": duel_id, "settled": True}
            push_user_event(challenger.id, payload)
            push_user_event(defender.id, {**payload, "won": result.get("won")})
        except Exception:
            logger.debug("duel_matched ws push skipped")
