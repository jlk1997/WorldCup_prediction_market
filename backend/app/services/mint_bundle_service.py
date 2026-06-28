"""Fulfill mint_bundle cash SKU: AI credits + optional whitelist mint access."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import MintEvent, MintReservation, Order, Product, User


class MintBundleService:
    def __init__(self, db: Session):
        self.db = db

    def grant(self, user: User, product: Product, order: Order) -> dict[str, Any]:
        if order.grant_result_json:
            return order.grant_result_json

        payload = product.grant_payload or {}
        result: dict[str, Any] = {"product_type": "mint_bundle", "sku": product.sku}

        from app.services.ai_billing_service import AiBillingService

        AiBillingService(self.db).grant_ai_pack(user, payload)
        if payload.get("ai_live_credits"):
            result["ai_live_credits"] = int(payload["ai_live_credits"])
        if payload.get("ai_refresh_credits"):
            result["ai_refresh_credits"] = int(payload["ai_refresh_credits"])

        from app.db.repositories.user_repository import WalletRepository

        wallet = WalletRepository(self.db)
        bonus = int(payload.get("bonus_coins") or 0)
        if product.coins_grant > 0:
            wallet.add_coins(user, product.coins_grant, "purchase", "order", order.id)
            result["coins_grant"] = product.coins_grant
        elif bonus > 0:
            wallet.add_coins(user, bonus, "purchase", "order", order.id)
            result["bonus_coins"] = bonus

        mint_event_id = payload.get("mint_event_id")
        if mint_event_id:
            mint_result = self._grant_mint_access(user, int(mint_event_id), order.id)
            result["mint_event_id"] = int(mint_event_id)
            result.update(mint_result)

        order.grant_result_json = result
        return result

    def _grant_mint_access(self, user: User, event_id: int, order_id: int) -> dict[str, Any]:
        event = (
            self.db.query(MintEvent)
            .filter(MintEvent.id == event_id)
            .with_for_update()
            .first()
        )
        if not event or not event.active:
            raise NotFoundError("打新活动不存在或已下线")

        existing = (
            self.db.query(MintReservation)
            .filter(MintReservation.event_id == event_id, MintReservation.user_id == user.id)
            .with_for_update()
            .first()
        )
        if existing:
            return {
                "mint_access": existing.status,
                "mint_access_already": True,
                "mint_event_name": event.name,
            }

        if event.sale_mode == "lottery":
            status = "won"
        elif event.sale_mode == "whitelist":
            status = "reserved"
        else:
            status = "reserved"

        res = MintReservation(
            event_id=event_id,
            user_id=user.id,
            status=status,
            claimed_count=0,
        )
        try:
            with self.db.begin_nested():
                self.db.add(res)
                self.db.flush()
        except IntegrityError:
            raced = (
                self.db.query(MintReservation)
                .filter(MintReservation.event_id == event_id, MintReservation.user_id == user.id)
                .first()
            )
            if raced:
                return {
                    "mint_access": raced.status,
                    "mint_access_already": True,
                    "mint_event_name": event.name,
                }
            raise
        return {
            "mint_access": status,
            "mint_access_granted": True,
            "mint_event_name": event.name,
            "mint_coupon_note": (event.description or "")[:120],
        }

    def bind_product_event(self, product: Product, mint_event_id: int) -> Product:
        if product.product_type != "mint_bundle":
            raise BadRequestError("仅 mint_bundle 商品可绑定打新活动")
        event = self.db.get(MintEvent, mint_event_id)
        if not event:
            raise NotFoundError("打新活动不存在")
        payload = dict(product.grant_payload or {})
        payload["mint_event_id"] = mint_event_id
        if not payload.get("mint_coupon_note"):
            payload["mint_coupon_note"] = f"含「{event.name}」白名单资格"
        from app.data.cash_grant_schema import validate_cash_grant_payload

        product.grant_payload = validate_cash_grant_payload(payload, product_type=product.product_type)
        product.description = product.description or f"组合包 · {event.name} 资格"
        self.db.commit()
        self.db.refresh(product)
        return product
