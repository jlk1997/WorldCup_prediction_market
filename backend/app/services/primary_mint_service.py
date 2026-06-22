"""一级首发打新：限量发行球星卡，预约/白名单/抽签，球迷币或人民币入场。

获客引擎：限量 + FOMO + 序列号稀缺。人民币入场为合规一级发行（非二级炒作）。
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import (
    CardTransferLog,
    CollectibleCard,
    MarketPricePoint,
    MintEvent,
    MintReservation,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PrimaryMintService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)

    def seed_demo_events(self) -> dict[str, Any]:
        """创建演示打新活动（绑定现有卡牌，幂等）。供运营/演示初始化。"""
        now = _utcnow()
        # 选取若干现有可发行卡牌（优先 epic/legend）
        cards = (
            self.db.query(CollectibleCard)
            .filter(CollectibleCard.active.is_(True))
            .order_by(CollectibleCard.id.asc())
            .all()
        )
        if not cards:
            return {"created": 0, "reason": "no_cards"}
        # 排序：legend → epic → rare → common
        order = {"legend": 0, "epic": 1, "rare": 2, "common": 3}
        cards.sort(key=lambda c: order.get(c.rarity, 9))

        specs = [
            {
                "suffix": "live_public",
                "name": "世界杯传奇首发 · 公开发售",
                "desc": "限量发行的传奇球星卡，序列号永久记录，错过即绝版。球迷币入场。",
                "sale_mode": "public",
                "currency": "coins",
                "price_coins": 200,
                "total": 500,
                "rstart": None,
                "start": now - timedelta(hours=1),
                "end": now + timedelta(days=3),
            },
            {
                "suffix": "reserve_lottery",
                "name": "史诗球星 · 抽签打新",
                "desc": "预约报名后抽签决定打新资格，公平限量。",
                "sale_mode": "lottery",
                "currency": "coins",
                "price_coins": 120,
                "total": 200,
                "rstart": now - timedelta(hours=2),
                "start": now + timedelta(days=1),
                "end": now + timedelta(days=4),
            },
            {
                "suffix": "upcoming_wl",
                "name": "联赛新星 · 白名单专属",
                "desc": "面向资深藏家的白名单限量发行，预约进入名单。",
                "sale_mode": "whitelist",
                "currency": "coins",
                "price_coins": 80,
                "total": 300,
                "rstart": now + timedelta(hours=6),
                "start": now + timedelta(days=2),
                "end": now + timedelta(days=6),
            },
        ]
        created = 0
        for i, spec in enumerate(specs):
            code = f"mint_demo_{spec['suffix']}"
            if self.db.query(MintEvent.id).filter(MintEvent.code == code).first():
                continue
            card = cards[i % len(cards)]
            ev = MintEvent(
                code=code,
                name=spec["name"],
                description=spec["desc"],
                card_code=card.code,
                image_url=card.image_url,
                rarity=card.rarity,
                competition="WorldCup2026",
                total_supply=spec["total"],
                issued=0,
                currency=spec["currency"],
                price_coins=spec["price_coins"],
                price_fen=0,
                per_user_limit=1,
                sale_mode=spec["sale_mode"],
                reserve_starts_at=spec["rstart"],
                starts_at=spec["start"],
                ends_at=spec["end"],
                status="scheduled",
                active=True,
            )
            self.db.add(ev)
            created += 1
        self.db.commit()
        return {"created": created}

    def _phase(self, event: MintEvent) -> str:
        now = _utcnow()
        if event.status in ("sold_out", "ended"):
            return event.status
        if event.issued >= event.total_supply:
            return "sold_out"
        if event.reserve_starts_at and now < event.reserve_starts_at:
            return "scheduled"
        if event.reserve_starts_at and now >= event.reserve_starts_at and now < event.starts_at:
            return "reserving"
        if now < event.starts_at:
            return "scheduled"
        if now > event.ends_at:
            return "ended"
        return "live"

    def list_events(self, user: User | None = None) -> list[dict[str, Any]]:
        events = (
            self.db.query(MintEvent)
            .filter(MintEvent.active.is_(True))
            .order_by(MintEvent.starts_at.asc())
            .all()
        )
        out = []
        reservations: dict[int, MintReservation] = {}
        if user:
            res_rows = (
                self.db.query(MintReservation)
                .filter(MintReservation.user_id == user.id, MintReservation.event_id.in_([e.id for e in events]))
                .all()
            ) if events else []
            reservations = {r.event_id: r for r in res_rows}
        for e in events:
            out.append(self._event_brief(e, reservations.get(e.id)))
        return out

    def _event_brief(self, event: MintEvent, reservation: MintReservation | None) -> dict[str, Any]:
        phase = self._phase(event)
        return {
            "id": event.id,
            "code": event.code,
            "name": event.name,
            "description": event.description,
            "card_code": event.card_code,
            "image_url": event.image_url,
            "rarity": event.rarity,
            "competition": event.competition,
            "total_supply": event.total_supply,
            "issued": event.issued,
            "remaining": max(0, event.total_supply - event.issued),
            "currency": event.currency,
            "price_coins": event.price_coins,
            "price_fen": event.price_fen,
            "per_user_limit": event.per_user_limit,
            "sale_mode": event.sale_mode,
            "phase": phase,
            "reserve_starts_at": event.reserve_starts_at.isoformat() if event.reserve_starts_at else None,
            "starts_at": event.starts_at.isoformat() if event.starts_at else None,
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            "reserved": reservation is not None,
            "reservation_status": reservation.status if reservation else None,
            "can_buy": self._can_buy(event, reservation, phase),
            "disclaimer": "一级限量发行，球星卡为站内虚拟藏品，无现金价值、不可提现。",
        }

    @staticmethod
    def _can_buy(event: MintEvent, reservation: MintReservation | None, phase: str) -> bool:
        if phase != "live" or event.issued >= event.total_supply:
            return False
        if event.sale_mode == "public":
            return True
        if event.sale_mode == "whitelist":
            return reservation is not None
        if event.sale_mode == "lottery":
            return reservation is not None and reservation.status == "won"
        return False

    def reserve(self, user: User, event_id: int) -> dict[str, Any]:
        event = self.db.get(MintEvent, event_id)
        if not event or not event.active:
            raise NotFoundError("活动不存在")
        phase = self._phase(event)
        if phase not in ("reserving", "scheduled", "live"):
            raise BadRequestError("当前不可预约")
        existing = (
            self.db.query(MintReservation)
            .filter(MintReservation.event_id == event_id, MintReservation.user_id == user.id)
            .first()
        )
        if existing:
            return {"ok": True, "status": existing.status, "already": True}
        status = "reserved"
        res = MintReservation(event_id=event_id, user_id=user.id, status=status)
        self.db.add(res)
        self.db.commit()
        return {"ok": True, "status": status}

    def draw_lottery(self, event_id: int) -> dict[str, int]:
        """抽签：从预约用户中按供应量随机选中（admin/scheduler）。"""
        event = self.db.get(MintEvent, event_id)
        if not event:
            raise NotFoundError("活动不存在")
        if event.sale_mode != "lottery":
            raise BadRequestError("非抽签活动")
        reservations = (
            self.db.query(MintReservation)
            .filter(MintReservation.event_id == event_id, MintReservation.status == "reserved")
            .all()
        )
        if not reservations:
            return {"won": 0, "lost": 0}
        winners = set()
        if len(reservations) <= event.total_supply:
            winners = {r.id for r in reservations}
        else:
            winners = {r.id for r in random.sample(reservations, event.total_supply)}
        won = lost = 0
        for r in reservations:
            if r.id in winners:
                r.status = "won"
                won += 1
            else:
                r.status = "lost"
                lost += 1
        self.db.commit()
        return {"won": won, "lost": lost}

    def purchase(self, user: User, event_id: int) -> dict[str, Any]:
        user_locked = (
            self.db.query(User).filter(User.id == user.id).with_for_update().first()
        )
        if not user_locked:
            raise NotFoundError("用户不存在")
        event = (
            self.db.query(MintEvent)
            .filter(MintEvent.id == event_id)
            .with_for_update()
            .first()
        )
        if not event or not event.active:
            raise NotFoundError("活动不存在")
        if self._phase(event) != "live":
            raise BadRequestError("不在发售时间内")
        if event.issued >= event.total_supply:
            event.status = "sold_out"
            raise BadRequestError("已售罄")

        # 销售模式校验
        reservation = (
            self.db.query(MintReservation)
            .filter(MintReservation.event_id == event_id, MintReservation.user_id == user_locked.id)
            .with_for_update()
            .first()
        )
        if event.sale_mode == "whitelist" and not reservation:
            raise BadRequestError("白名单专属，未在名单内")
        if event.sale_mode == "lottery":
            if not reservation or reservation.status != "won":
                raise BadRequestError("抽签未中签")
        claimed = reservation.claimed_count if reservation else 0
        if claimed >= event.per_user_limit:
            raise BadRequestError("已达个人限购")

        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == event.card_code).first()
        if not card:
            raise NotFoundError("发行卡牌不存在")
        owns = (
            self.db.query(UserCollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user_locked.id, UserCollectibleCard.card_id == card.id)
            .first()
        )
        if owns:
            raise BadRequestError("你已拥有该卡，限量发行每人一张序列")

        # 支付
        if event.currency == "coins":
            if (user_locked.fan_coins or 0) < event.price_coins:
                raise BadRequestError("球迷币不足")
            self.wallet.deduct_coins(user_locked, event.price_coins, "mint_purchase", "mint_event", event.id)
            price_points_equiv = event.price_coins
        elif event.currency == "rmb":
            # 人民币一级发行须走支付下单流程；此处要求先充值球迷币或对接订单
            raise BadRequestError("人民币首发请通过订单支付完成（敬请期待）")
        else:
            raise BadRequestError("不支持的支付方式")

        # 发行：授予卡牌（带序列号）
        from app.services.collectible_service import CollectibleService

        grant = CollectibleService(self.db)._grant_card(user_locked, card, "primary")
        if grant.get("is_duplicate"):
            self.wallet.add_coins(
                user_locked, event.price_coins, "mint_purchase_refund", "mint_event", event.id
            )
            self.db.commit()
            raise BadRequestError("你已拥有该卡，球迷币已自动退还")
        user_card_id = grant.get("user_card_id")
        event.issued = (event.issued or 0) + 1
        if event.issued >= event.total_supply:
            event.status = "sold_out"

        if not reservation:
            reservation = MintReservation(event_id=event_id, user_id=user_locked.id, status="claimed", claimed_count=0)
            self.db.add(reservation)
            self.db.flush()
        reservation.claimed_count = (reservation.claimed_count or 0) + 1
        reservation.status = "claimed"

        # 行情首发点 + 流水
        self.db.add(
            MarketPricePoint(card_id=card.id, price_points=price_points_equiv, qty=1, kind="primary")
        )
        self.db.add(
            CardTransferLog(
                card_id=card.id,
                user_card_id=user_card_id,
                from_user_id=None,
                to_user_id=user_locked.id,
                kind="primary",
                points_amount=price_points_equiv,
                note=f"mint:{event.code}",
            )
        )
        try:
            from app.services.card_asset_service import CardAssetService

            CardAssetService(self.db).evaluate_achievements(user_locked)
        except Exception:
            pass
        self.db.commit()
        return {
            "ok": True,
            "card_code": card.code,
            "card_name": card.name,
            "serial_no": grant.get("serial_no") or (
                self.db.get(UserCollectibleCard, user_card_id).serial_no if user_card_id else None
            ),
            "remaining": max(0, event.total_supply - event.issued),
            "notice": "打新成功！已获得限量序列球星卡（站内虚拟藏品）",
        }

    def draw_pending_lotteries(self, limit: int = 20) -> dict[str, int]:
        """开售时自动抽签（scheduler 周期调用）。"""
        now = _utcnow()
        events = (
            self.db.query(MintEvent)
            .filter(
                MintEvent.active.is_(True),
                MintEvent.sale_mode == "lottery",
                MintEvent.starts_at <= now,
            )
            .limit(limit)
            .all()
        )
        drawn = skipped = 0
        for event in events:
            pending = (
                self.db.query(MintReservation.id)
                .filter(
                    MintReservation.event_id == event.id,
                    MintReservation.status == "reserved",
                )
                .first()
            )
            if not pending:
                skipped += 1
                continue
            try:
                self.draw_lottery(event.id)
                drawn += 1
            except BadRequestError:
                skipped += 1
        return {"drawn": drawn, "skipped": skipped}

    def seed_collab_events(self) -> dict[str, Any]:
        """为联名卡创建打新活动（幂等）。"""
        from app.data.collab_catalog import COLLAB_CARDS
        from app.services.collectible_service import CollectibleService

        CollectibleService(self.db).seed_collab_cards()
        now = _utcnow()
        created = 0
        for spec in COLLAB_CARDS:
            code = f"mint_collab_{spec['code']}"
            if self.db.query(MintEvent.id).filter(MintEvent.code == code).first():
                continue
            ev = MintEvent(
                code=code,
                name=f"联名首发 · {spec['name']}",
                description=spec.get("description") or "平台授权联名虚拟藏品",
                card_code=spec["code"],
                image_url=spec.get("image_url"),
                rarity=spec["rarity"],
                competition="Collab2026",
                total_supply=min(spec.get("mint_total") or 300, 300),
                issued=0,
                currency="coins",
                price_coins=150 if spec["rarity"] == "legend" else 80,
                price_fen=0,
                per_user_limit=1,
                sale_mode="public",
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=7),
                status="scheduled",
                active=True,
            )
            self.db.add(ev)
            created += 1
        self.db.commit()
        return {"created": created}
