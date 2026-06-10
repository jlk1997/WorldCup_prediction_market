"""Points redemption shop."""

from __future__ import annotations

import logging
import secrets

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import Product, RedeemOrder, User, UserBadge
from app.db.repositories.user_repository import WalletRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class RedeemShopService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet = WalletRepository(db)

    def list_products(self) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(Product.active.is_(True), Product.pay_currency == "redeem")
            .order_by(Product.featured.desc(), Product.sort_order, Product.id)
            .all()
        )

    def list_products_enriched(self, user: User | None) -> list[dict]:
        products = self.list_products()
        user_counts: dict[int, int] = {}
        if user:
            rows = (
                self.db.query(RedeemOrder.product_id, RedeemOrder.id)
                .filter(RedeemOrder.user_id == user.id, RedeemOrder.status == "completed")
                .all()
            )
            for pid, _ in rows:
                user_counts[pid] = user_counts.get(pid, 0) + 1
        out = []
        for p in products:
            purchased = user_counts.get(p.id, 0)
            blocked = self._blocked_reason(p, purchased, user)
            out.append(
                {
                    "product": p,
                    "user_purchased_count": purchased,
                    "stock_remaining": p.stock_remaining(),
                    "is_unlimited_stock": (p.stock_total or 0) <= 0,
                    "is_out_of_stock": p.is_out_of_stock(),
                    "can_purchase": blocked is None,
                    "purchase_blocked_reason": blocked,
                }
            )
        return out

    def list_user_orders(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = (
            self.db.query(RedeemOrder, Product)
            .join(Product, RedeemOrder.product_id == Product.id)
            .filter(RedeemOrder.user_id == user_id)
            .order_by(RedeemOrder.id.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [
            {
                "id": order.id,
                "product_id": order.product_id,
                "redeem_price": order.redeem_price,
                "status": order.status,
                "created_at": order.created_at,
                "product_name": product.name,
            }
            for order, product in rows
        ]

    def purchase(
        self,
        user_id: int,
        product_id: int,
        idempotency_key: str | None = None,
    ) -> dict:
        idem = (idempotency_key or "").strip() or secrets.token_hex(16)
        existing = (
            self.db.query(RedeemOrder)
            .filter(
                RedeemOrder.user_id == user_id,
                RedeemOrder.idempotency_key == idem,
            )
            .first()
        )
        if existing:
            user = self.db.get(User, user_id)
            product = self.db.get(Product, existing.product_id)
            return {
                "order": existing,
                "redeem_points_after": user.redeem_points if user else 0,
                "stock_remaining": product.stock_remaining() if product else None,
                "idempotent_replay": True,
            }

        product = (
            self.db.query(Product)
            .filter(Product.id == product_id)
            .with_for_update()
            .first()
        )
        if not product or not product.active or product.pay_currency != "redeem":
            raise NotFoundError("兑换商品不存在")
        if not product.redeem_price or product.redeem_price <= 0:
            raise BadRequestError("商品未配置兑换价格")

        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            raise NotFoundError("用户不存在")

        purchased = (
            self.db.query(RedeemOrder)
            .filter(
                RedeemOrder.user_id == user_id,
                RedeemOrder.product_id == product_id,
                RedeemOrder.status == "completed",
            )
            .count()
        )
        blocked = self._blocked_reason(product, purchased, user)
        if blocked:
            messages = {
                "out_of_stock": "商品已兑完",
                "per_user_limit": "已达个人兑换上限",
                "insufficient_points": "可用积分不足",
            }
            raise BadRequestError(messages.get(blocked, "无法兑换"))
        if (user.redeem_points or 0) < product.redeem_price:
            raise BadRequestError("可用积分不足")

        self.wallet.deduct_redeem_points(
            user, product.redeem_price, "redeem_purchase", "product", product.id
        )
        self._apply_grant_payload(user, product)
        if (product.stock_total or 0) > 0:
            product.stock_sold = (product.stock_sold or 0) + 1

        order = RedeemOrder(
            user_id=user_id,
            product_id=product.id,
            redeem_price=product.redeem_price,
            status="completed",
            idempotency_key=idem,
        )
        self.db.add(order)
        self.db.flush()

        try:
            NotificationService(self.db).notify_redeem_success(
                user_id,
                order.id,
                product.name,
                product.redeem_price,
                user.redeem_points or 0,
            )
        except Exception:
            logger.exception("Redeem notification failed")

        self.db.commit()
        self.db.refresh(order)
        return {
            "order": order,
            "redeem_points_after": user.redeem_points or 0,
            "stock_remaining": product.stock_remaining(),
            "idempotent_replay": False,
        }

    def _blocked_reason(self, product: Product, purchased: int, user: User | None) -> str | None:
        if product.is_out_of_stock():
            return "out_of_stock"
        limit = product.per_user_limit or 0
        if limit > 0 and purchased >= limit:
            return "per_user_limit"
        if user and product.redeem_price and (user.redeem_points or 0) < product.redeem_price:
            return "insufficient_points"
        return None

    def _apply_grant_payload(self, user: User, product: Product) -> None:
        payload = product.grant_payload or {}
        if not payload:
            return
        if frame := payload.get("avatar_frame"):
            user.avatar_frame = str(frame)
        if theme := payload.get("theme_key"):
            user.theme_key = str(theme)
        extra = payload.get("extra_free_predict_daily")
        if extra:
            user.extra_free_predict_daily = (user.extra_free_predict_daily or 0) + int(extra)
        badge_code = payload.get("badge_code")
        if badge_code:
            exists = (
                self.db.query(UserBadge)
                .filter(UserBadge.user_id == user.id, UserBadge.badge_code == badge_code)
                .first()
            )
            if not exists:
                self.db.add(
                    UserBadge(
                        user_id=user.id,
                        badge_code=str(badge_code),
                        title=str(payload.get("badge_title") or badge_code),
                    )
                )

    def _revoke_grant_payload(self, user: User, product: Product) -> None:
        payload = product.grant_payload or {}
        if not payload:
            return
        if frame := payload.get("avatar_frame"):
            if user.avatar_frame == str(frame):
                user.avatar_frame = None
        if theme := payload.get("theme_key"):
            if user.theme_key == str(theme):
                user.theme_key = None
        extra = payload.get("extra_free_predict_daily")
        if extra:
            user.extra_free_predict_daily = max(0, (user.extra_free_predict_daily or 0) - int(extra))

    def admin_refund_order(self, order_id: int) -> dict:
        order = (
            self.db.query(RedeemOrder)
            .filter(RedeemOrder.id == order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise NotFoundError("兑换订单不存在")
        if order.status != "completed":
            raise BadRequestError("仅可撤销已完成的兑换订单")
        product = (
            self.db.query(Product)
            .filter(Product.id == order.product_id)
            .with_for_update()
            .first()
        )
        user = self.db.query(User).filter(User.id == order.user_id).with_for_update().first()
        if not product or not user:
            raise NotFoundError("订单关联数据不存在")
        self.wallet.add_redeem_points(
            user,
            order.redeem_price,
            "redeem_refund",
            "redeem_order",
            order.id,
        )
        self._revoke_grant_payload(user, product)
        if (product.stock_total or 0) > 0 and (product.stock_sold or 0) > 0:
            product.stock_sold -= 1
        order.status = "refunded"
        try:
            NotificationService(self.db).notify_redeem_refund(
                user.id,
                order.id,
                product.name,
                order.redeem_price,
                user.redeem_points or 0,
            )
        except Exception:
            logger.exception("Redeem refund notification failed order=%s", order.id)
        self.db.commit()
        self.db.refresh(order)
        return {
            "order_id": order.id,
            "status": order.status,
            "redeem_points_after": user.redeem_points or 0,
            "stock_remaining": product.stock_remaining(),
        }
