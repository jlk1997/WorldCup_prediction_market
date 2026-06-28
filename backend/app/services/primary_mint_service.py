"""一级首发打新：限量发行球星卡，预约/白名单/抽签，球迷币或人民币入场。

获客引擎：限量 + FOMO + 序列号稀缺。人民币入场为合规一级发行（非二级炒作）。
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import (
    CardTransferLog,
    CollectibleCard,
    MarketPricePoint,
    MintEvent,
    MintReservation,
    Order,
    Product,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository
from app.utils.pay_channel import PayChannel, PayChannelRequest, resolve_pay_channel

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
            {
                "suffix": "live_rmb",
                "name": "传奇限定 · 人民币首发",
                "desc": "限量传奇球星卡人民币一级发行，序列号永久记录。",
                "sale_mode": "public",
                "currency": "rmb",
                "price_coins": 0,
                "price_fen": 6800,
                "total": 100,
                "rstart": None,
                "start": now - timedelta(hours=1),
                "end": now + timedelta(days=5),
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
                price_fen=spec.get("price_fen", 0),
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
        remaining = self.available_supply(event)
        pending_payment = bool(
            reservation
            and reservation.status == "payment_pending"
            and reservation.lock_expires_at
            and reservation.lock_expires_at > _utcnow()
        )
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
            "remaining": remaining,
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
            "pending_payment": pending_payment,
            "can_buy": self._can_buy(event, reservation, phase) and remaining > 0,
            "disclaimer": "一级限量发行，球星卡为站内虚拟藏品，无现金价值、不可提现。",
        }

    @staticmethod
    def _can_buy(event: MintEvent, reservation: MintReservation | None, phase: str) -> bool:
        if phase != "live" or event.issued >= event.total_supply:
            return False
        if reservation and reservation.status == "payment_pending":
            if reservation.lock_expires_at and reservation.lock_expires_at > _utcnow():
                return True
        if event.sale_mode == "public":
            return True
        if event.sale_mode == "whitelist":
            return reservation is not None
        if event.sale_mode == "lottery":
            return reservation is not None and reservation.status == "won"
        return False

    def _active_pending_locks(self, event_id: int) -> int:
        now = _utcnow()
        return (
            self.db.query(MintReservation.id)
            .filter(
                MintReservation.event_id == event_id,
                MintReservation.status == "payment_pending",
                MintReservation.lock_expires_at.isnot(None),
                MintReservation.lock_expires_at > now,
            )
            .count()
        )

    def available_supply(self, event: MintEvent) -> int:
        locked = self._active_pending_locks(event.id)
        return max(0, event.total_supply - (event.issued or 0) - locked)

    def ensure_mint_product(self, event: MintEvent) -> Product:
        sku = f"mint_event_{event.code}"
        product = self.db.query(Product).filter(Product.sku == sku).first()
        if not product:
            product = Product(
                sku=sku,
                name=event.name,
                description=event.description,
                price_fen=event.price_fen,
                coins_grant=0,
                grant_season_pass_days=0,
                product_type="mint_event",
                pay_currency="cash",
                grant_payload={"mint_event_id": event.id},
                per_user_limit=event.per_user_limit,
                active=event.active,
                sort_order=9000 + event.id,
            )
            self.db.add(product)
            self.db.flush()
        else:
            product.name = event.name
            product.description = event.description
            product.price_fen = event.price_fen
            product.per_user_limit = event.per_user_limit
            product.active = event.active
            payload = dict(product.grant_payload or {})
            payload["mint_event_id"] = event.id
            product.grant_payload = payload
        return product

    def _get_or_create_reservation(
        self, event_id: int, user_id: int, *, for_update: bool = False
    ) -> MintReservation | None:
        q = self.db.query(MintReservation).filter(
            MintReservation.event_id == event_id,
            MintReservation.user_id == user_id,
        )
        if for_update:
            q = q.with_for_update()
        return q.first()

    def _validate_mint_eligibility(
        self,
        user: User,
        event: MintEvent,
        reservation: MintReservation | None,
        *,
        skip_payment_pending: bool = False,
    ) -> CollectibleCard:
        if event.currency != "rmb" and event.currency != "coins":
            raise BadRequestError("不支持的支付方式")
        if self._phase(event) != "live":
            raise BadRequestError("不在发售时间内")
        if event.issued >= event.total_supply:
            event.status = "sold_out"
            raise BadRequestError("已售罄")
        if self.available_supply(event) <= 0 and not (
            reservation
            and reservation.status == "payment_pending"
            and reservation.lock_expires_at
            and reservation.lock_expires_at > _utcnow()
        ):
            raise BadRequestError("库存已满，请稍后再试")

        if event.sale_mode == "whitelist" and not reservation:
            raise BadRequestError("白名单专属，未在名单内")
        if event.sale_mode == "lottery":
            if not reservation or reservation.status != "won":
                if reservation and reservation.status == "payment_pending":
                    pass
                else:
                    raise BadRequestError("抽签未中签")
        claimed = reservation.claimed_count if reservation else 0
        if claimed >= event.per_user_limit:
            raise BadRequestError("已达个人限购")
        if reservation and reservation.status == "payment_pending" and not skip_payment_pending:
            if reservation.lock_expires_at and reservation.lock_expires_at > _utcnow():
                raise BadRequestError("已有待支付订单，请先完成或取消支付")

        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == event.card_code).first()
        if not card:
            raise NotFoundError("发行卡牌不存在")
        owns = (
            self.db.query(UserCollectibleCard.id)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
            .first()
        )
        if owns:
            raise BadRequestError("你已拥有该卡，限量发行每人一张序列")
        return card

    def _apply_mint_lock(
        self, event: MintEvent, user_id: int, order: Order, reservation: MintReservation | None
    ) -> MintReservation:
        lock_until = _utcnow() + timedelta(minutes=self.settings.order_pending_reuse_minutes)
        if not reservation:
            reservation = MintReservation(
                event_id=event.id,
                user_id=user_id,
                status="payment_pending",
                claimed_count=0,
            )
            self.db.add(reservation)
            self.db.flush()
        reservation.status = "payment_pending"
        reservation.pending_order_id = order.id
        reservation.lock_expires_at = lock_until
        order.mint_event_id = event.id
        return reservation

    def release_mint_lock_for_order(self, order: Order) -> None:
        if not order.mint_event_id:
            return
        reservation = (
            self.db.query(MintReservation)
            .filter(
                MintReservation.pending_order_id == order.id,
                MintReservation.event_id == order.mint_event_id,
            )
            .with_for_update()
            .first()
        )
        if not reservation or reservation.status != "payment_pending":
            return
        if (reservation.claimed_count or 0) > 0:
            reservation.status = "claimed"
        else:
            event = self.db.get(MintEvent, order.mint_event_id)
            if event and event.sale_mode == "lottery":
                reservation.status = "won"
            else:
                reservation.status = "reserved"
        reservation.pending_order_id = None
        reservation.lock_expires_at = None

    def create_rmb_order(
        self,
        user: User,
        event_id: int,
        *,
        pay_channel: PayChannelRequest = "auto",
        user_agent: str | None = None,
    ) -> tuple[Order, str, PayChannel]:
        from app.services.card_asset_service import CardAssetService

        CardAssetService(self.db).assert_real_name(user)

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
        if event.currency != "rmb":
            raise BadRequestError("该活动不支持人民币支付")
        if event.price_fen <= 0:
            raise BadRequestError("活动价格未配置")

        reservation = self._get_or_create_reservation(event_id, user_locked.id, for_update=True)
        self._validate_mint_eligibility(user_locked, event, reservation)

        from app.services.payment_service import PaymentService

        payment = PaymentService(self.db, self.settings)
        product = self.ensure_mint_product(event)

        reuse_cutoff = _utcnow() - timedelta(minutes=self.settings.order_pending_reuse_minutes)
        existing = (
            self.db.query(Order)
            .filter(
                Order.user_id == user_locked.id,
                Order.mint_event_id == event.id,
                Order.status == "pending",
                Order.created_at >= reuse_cutoff,
            )
            .order_by(Order.id.desc())
            .first()
        )
        channel = resolve_pay_channel(pay_channel, user_agent)
        if existing:
            if existing.amount_fen != event.price_fen:
                existing.amount_fen = event.price_fen
            self._apply_mint_lock(event, user_locked.id, existing, reservation)
            self.db.commit()
            self.db.refresh(existing)
            pay_url = payment._build_pay_url(existing, product, channel)
            return existing, pay_url, channel

        import uuid

        out_trade_no = f"WC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
        order = Order(
            out_trade_no=out_trade_no,
            user_id=user_locked.id,
            product_id=product.id,
            mint_event_id=event.id,
            amount_fen=event.price_fen,
            status="pending",
        )
        self.db.add(order)
        self.db.flush()
        self._apply_mint_lock(event, user_locked.id, order, reservation)
        self.db.commit()
        self.db.refresh(order)
        pay_url = payment._build_pay_url(order, product, channel)
        return order, pay_url, channel

    def fulfill_paid_order(self, order: Order) -> dict[str, Any]:
        """支付成功后发卡（幂等）。"""
        if order.grant_result_json:
            return order.grant_result_json

        if not order.mint_event_id:
            payload = (self.db.get(Product, order.product_id).grant_payload or {}) if order.product_id else {}
            mint_event_id = payload.get("mint_event_id")
            if mint_event_id:
                order.mint_event_id = int(mint_event_id)

        event = (
            self.db.query(MintEvent)
            .filter(MintEvent.id == order.mint_event_id)
            .with_for_update()
            .first()
        )
        if not event:
            raise NotFoundError("打新活动不存在")

        user = (
            self.db.query(User).filter(User.id == order.user_id).with_for_update().first()
        )
        if not user:
            raise NotFoundError("用户不存在")

        reservation = self._get_or_create_reservation(event.id, user.id, for_update=True)
        card = self._validate_mint_eligibility(
            user, event, reservation, skip_payment_pending=True
        )

        from app.services.collectible_service import CollectibleService

        grant = CollectibleService(self.db)._grant_card(user, card, "primary")
        if grant.get("is_duplicate"):
            raise BadRequestError("你已拥有该卡，请联系客服处理退款")

        user_card_id = grant.get("user_card_id")
        event.issued = (event.issued or 0) + 1
        if event.issued >= event.total_supply:
            event.status = "sold_out"

        price_points_equiv = max(1, event.price_fen // 10)
        if not reservation:
            reservation = MintReservation(
                event_id=event.id, user_id=user.id, status="claimed", claimed_count=0
            )
            self.db.add(reservation)
            self.db.flush()
        reservation.claimed_count = (reservation.claimed_count or 0) + 1
        reservation.status = "claimed"
        reservation.pending_order_id = None
        reservation.lock_expires_at = None

        self.db.add(
            MarketPricePoint(card_id=card.id, price_points=price_points_equiv, qty=1, kind="primary")
        )
        self.db.add(
            CardTransferLog(
                card_id=card.id,
                user_card_id=user_card_id,
                from_user_id=None,
                to_user_id=user.id,
                kind="primary",
                points_amount=price_points_equiv,
                note=f"mint:{event.code}:order:{order.id}",
            )
        )
        try:
            from app.services.card_asset_service import CardAssetService

            CardAssetService(self.db).evaluate_achievements(user)
        except Exception:
            pass

        serial_no = grant.get("serial_no")
        if not serial_no and user_card_id:
            uc = self.db.get(UserCollectibleCard, user_card_id)
            serial_no = uc.serial_no if uc else None

        result = {
            "ok": True,
            "card_code": card.code,
            "card_name": card.name,
            "serial_no": serial_no,
            "user_card_id": user_card_id,
            "remaining": max(0, event.total_supply - event.issued),
            "notice": "打新成功！已获得限量序列球星卡（站内虚拟藏品）",
        }
        order.grant_result_json = result

        try:
            from app.services.notification_service import NotificationService

            NotificationService(self.db).notify_mint_purchase_success(
                user.id, card.name, serial_no, order.id
            )
        except Exception:
            logger.debug("mint purchase notification skipped", exc_info=True)

        return result

    def cancel_pending_order(self, user: User, order: Order) -> Order:
        if order.user_id != user.id:
            raise BadRequestError("无权操作该订单")
        if order.status != "pending":
            raise BadRequestError("仅待支付订单可取消")
        order.status = "cancelled"
        self.release_mint_lock_for_order(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def expire_pending_mint_orders(self, limit: int = 100) -> dict[str, int]:
        now = _utcnow()
        rows = (
            self.db.query(Order)
            .filter(
                Order.mint_event_id.isnot(None),
                Order.status == "pending",
            )
            .order_by(Order.id.asc())
            .limit(limit)
            .all()
        )
        expired = skipped = 0
        for order in rows:
            reservation = (
                self.db.query(MintReservation)
                .filter(MintReservation.pending_order_id == order.id)
                .first()
            )
            lock_deadline = reservation.lock_expires_at if reservation else None
            reuse_deadline = (order.created_at or now) + timedelta(
                minutes=self.settings.order_pending_reuse_minutes
            )
            if lock_deadline and lock_deadline > now and reuse_deadline > now:
                skipped += 1
                continue
            order.status = "cancelled"
            self.release_mint_lock_for_order(order)
            expired += 1
        if expired:
            self.db.commit()
        return {"expired": expired, "skipped": skipped}

    def sync_event_statuses(self, limit: int = 50) -> dict[str, int]:
        """根据时间自动更新打新活动状态（运营编排）。"""
        now = _utcnow()
        events = (
            self.db.query(MintEvent)
            .filter(MintEvent.active.is_(True))
            .order_by(MintEvent.starts_at.asc())
            .limit(limit)
            .all()
        )
        updated = 0
        for event in events:
            phase = self._phase(event)
            new_status = event.status
            if phase == "sold_out":
                new_status = "sold_out"
            elif phase == "ended":
                new_status = "ended"
            elif phase == "live":
                new_status = "live"
            elif phase in ("reserving", "scheduled"):
                new_status = "scheduled"
            if new_status != event.status:
                event.status = new_status
                updated += 1
        if updated:
            self.db.commit()
        return {"updated": updated}

    def admin_list_events(self) -> list[dict[str, Any]]:
        events = self.db.query(MintEvent).order_by(MintEvent.id.desc()).limit(100).all()
        return [self._admin_event_row(e) for e in events]

    @staticmethod
    def _admin_event_row(event: MintEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "code": event.code,
            "name": event.name,
            "card_code": event.card_code,
            "currency": event.currency,
            "price_coins": event.price_coins,
            "price_fen": event.price_fen,
            "total_supply": event.total_supply,
            "issued": event.issued,
            "sale_mode": event.sale_mode,
            "status": event.status,
            "active": event.active,
            "starts_at": event.starts_at.isoformat() if event.starts_at else None,
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            "reserve_starts_at": event.reserve_starts_at.isoformat() if event.reserve_starts_at else None,
        }

    def admin_create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        code = (payload.get("code") or "").strip()
        if not code:
            raise BadRequestError("code 必填")
        if self.db.query(MintEvent.id).filter(MintEvent.code == code).first():
            raise BadRequestError("活动 code 已存在")
        card_code = payload.get("card_code")
        if not card_code or not self.db.query(CollectibleCard.code).filter(CollectibleCard.code == card_code).first():
            raise BadRequestError("card_code 无效")
        now = _utcnow()
        starts = payload.get("starts_at") or now
        ends = payload.get("ends_at") or (now + timedelta(days=7))
        if isinstance(starts, str):
            starts = datetime.fromisoformat(starts.replace("Z", "+00:00")).replace(tzinfo=None)
        if isinstance(ends, str):
            ends = datetime.fromisoformat(ends.replace("Z", "+00:00")).replace(tzinfo=None)
        ev = MintEvent(
            code=code,
            name=payload.get("name") or code,
            description=payload.get("description"),
            card_code=card_code,
            image_url=payload.get("image_url"),
            rarity=payload.get("rarity") or "epic",
            competition=payload.get("competition"),
            total_supply=int(payload.get("total_supply") or 100),
            issued=0,
            currency=payload.get("currency") or "rmb",
            price_coins=int(payload.get("price_coins") or 0),
            price_fen=int(payload.get("price_fen") or 0),
            per_user_limit=int(payload.get("per_user_limit") or 1),
            sale_mode=payload.get("sale_mode") or "public",
            reserve_starts_at=payload.get("reserve_starts_at"),
            starts_at=starts,
            ends_at=ends,
            status=payload.get("status") or "scheduled",
            active=payload.get("active", True) is not False,
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        if ev.currency == "rmb" and ev.price_fen > 0:
            self.ensure_mint_product(ev)
            self.db.commit()
        return self._admin_event_row(ev)

    def admin_update_event(self, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        event = self.db.get(MintEvent, event_id)
        if not event:
            raise NotFoundError("活动不存在")
        for key in ("name", "description", "image_url", "competition", "status", "sale_mode", "currency"):
            if key in payload and payload[key] is not None:
                setattr(event, key, payload[key])
        for key in ("total_supply", "price_coins", "price_fen", "per_user_limit"):
            if key in payload and payload[key] is not None:
                setattr(event, key, int(payload[key]))
        if "active" in payload:
            event.active = bool(payload["active"])
        if payload.get("starts_at"):
            event.starts_at = datetime.fromisoformat(str(payload["starts_at"]).replace("Z", "+00:00")).replace(tzinfo=None)
        if payload.get("ends_at"):
            event.ends_at = datetime.fromisoformat(str(payload["ends_at"]).replace("Z", "+00:00")).replace(tzinfo=None)
        if event.currency == "rmb":
            self.ensure_mint_product(event)
        self.db.commit()
        self.db.refresh(event)
        return self._admin_event_row(event)

    def reserve(self, user: User, event_id: int) -> dict[str, Any]:
        event = self.db.get(MintEvent, event_id)
        if not event or not event.active:
            raise NotFoundError("活动不存在")
        phase = self._phase(event)
        premium_early = False
        try:
            from app.services.collection_pass_service import CollectionPassService

            progress = CollectionPassService(self.db)._get_or_create_progress(
                user, CollectionPassService(self.db)._get_active_season()
            )
            premium_early = bool(progress.premium_unlocked)
        except Exception:
            pass
        allowed_phases = ("reserving", "scheduled", "live")
        if premium_early and phase == "scheduled":
            allowed_phases = ("scheduled", "reserving", "live")
        if phase not in allowed_phases:
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
            raise BadRequestError("人民币首发请通过 create-order 接口下单支付")
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
            "user_card_id": user_card_id,
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
