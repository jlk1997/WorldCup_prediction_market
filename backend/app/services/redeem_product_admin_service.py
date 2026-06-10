"""Admin CRUD for redeem shop products (database source of truth)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.data.redeem_grant_schema import validate_grant_payload
from app.db.models.commerce import Product, RedeemOrder


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RedeemProductAdminService:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(Product.pay_currency == "redeem")
            .order_by(Product.sort_order, Product.id)
            .all()
        )

    def get(self, product_id: int) -> Product:
        product = self._get_redeem_product(product_id)
        if not product:
            raise NotFoundError("积分商品不存在")
        return product

    def create(
        self,
        *,
        sku: str,
        name: str,
        redeem_price: int,
        description: str | None = None,
        grant_payload: dict | None = None,
        per_user_limit: int = 0,
        stock_total: int = 0,
        sort_order: int = 0,
        featured: bool = False,
        active: bool = True,
    ) -> Product:
        sku = sku.strip()
        if not sku:
            raise BadRequestError("sku 不能为空")
        exists = self.db.query(Product.id).filter(Product.sku == sku).first()
        if exists:
            raise BadRequestError("sku 已存在")
        if redeem_price <= 0:
            raise BadRequestError("redeem_price 必须大于 0")
        payload = validate_grant_payload(grant_payload)
        product = Product(
            sku=sku,
            name=name.strip(),
            description=description,
            price_fen=0,
            coins_grant=0,
            grant_season_pass_days=0,
            product_type="redeem",
            pay_currency="redeem",
            redeem_price=redeem_price,
            grant_payload=payload,
            per_user_limit=max(0, per_user_limit),
            stock_total=max(0, stock_total),
            stock_sold=0,
            sort_order=sort_order,
            featured=featured,
            active=active,
            updated_at=_utcnow(),
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(
        self,
        product_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        redeem_price: int | None = None,
        grant_payload: dict | None = None,
        per_user_limit: int | None = None,
        stock_total: int | None = None,
        sort_order: int | None = None,
        featured: bool | None = None,
        active: bool | None = None,
        grant_payload_set: bool = False,
    ) -> Product:
        product = self.get(product_id)
        if name is not None:
            product.name = name.strip()
        if description is not None:
            product.description = description
        if redeem_price is not None:
            if redeem_price <= 0:
                raise BadRequestError("redeem_price 必须大于 0")
            product.redeem_price = redeem_price
        if grant_payload_set:
            product.grant_payload = validate_grant_payload(grant_payload)
        if per_user_limit is not None:
            product.per_user_limit = max(0, per_user_limit)
        if stock_total is not None:
            total = max(0, stock_total)
            sold = product.stock_sold or 0
            if total > 0 and sold > total:
                raise BadRequestError(f"stock_total 不能小于已兑数量 stock_sold={sold}")
            product.stock_total = total
        if sort_order is not None:
            product.sort_order = sort_order
        if featured is not None:
            product.featured = featured
        if active is not None:
            product.active = active
        product.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(product)
        return product

    def toggle_active(self, product_id: int) -> Product:
        product = self.get(product_id)
        product.active = not product.active
        product.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(product)
        return product

    def _get_redeem_product(self, product_id: int) -> Product | None:
        return (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.pay_currency == "redeem")
            .first()
        )

    @staticmethod
    def count_redeem_products(db: Session) -> int:
        return (
            db.query(Product)
            .filter(Product.pay_currency == "redeem", Product.active.is_(True))
            .count()
        )

    @staticmethod
    def has_orders(db: Session, product_id: int) -> bool:
        return (
            db.query(RedeemOrder.id)
            .filter(RedeemOrder.product_id == product_id)
            .first()
            is not None
        )
