"""Sync redeem product catalog from code to database."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data.redeem_grant_schema import GRANT_PAYLOAD_SCHEMA, validate_grant_payload
from app.data.redeem_product_catalog import REDEEM_PRODUCTS
from app.db.models.commerce import Product

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class ProductCatalogService:
    def __init__(self, db: Session):
        self.db = db

    def catalog_docs(self) -> dict:
        from app.services.redeem_product_admin_service import RedeemProductAdminService

        return {
            "grant_payload_schema": GRANT_PAYLOAD_SCHEMA,
            "catalog_source": "database:products",
            "total_in_catalog": RedeemProductAdminService.count_redeem_products(self.db),
        }

    def sync_redeem_catalog(self, *, deactivate_missing: bool = False) -> dict:
        seen_skus: set[str] = set()
        created = updated = 0
        for item in REDEEM_PRODUCTS:
            sku = item["sku"]
            seen_skus.add(sku)
            product = self.db.query(Product).filter(Product.sku == sku).first()
            stock_total = int(item.get("stock_total") or 0)
            if product:
                if stock_total > 0 and (product.stock_sold or 0) > stock_total:
                    logger.warning(
                        "SKU %s: stock_total %s below stock_sold %s, keeping sold count",
                        sku,
                        stock_total,
                        product.stock_sold,
                    )
                    stock_total = max(stock_total, product.stock_sold or 0)
                product.name = item["name"]
                product.description = item.get("description")
                product.price_fen = 0
                product.coins_grant = 0
                product.grant_season_pass_days = 0
                product.product_type = "redeem"
                product.pay_currency = "redeem"
                product.redeem_price = int(item["redeem_price"])
                product.grant_payload = validate_grant_payload(item.get("grant_payload"))
                product.per_user_limit = int(item.get("per_user_limit") or 0)
                product.stock_total = stock_total
                product.sort_order = int(item.get("sort_order") or 0)
                product.featured = bool(item.get("featured", False))
                product.active = True
                product.updated_at = _utcnow()
                updated += 1
            else:
                self.db.add(
                    Product(
                        sku=sku,
                        name=item["name"],
                        description=item.get("description"),
                        price_fen=0,
                        coins_grant=0,
                        grant_season_pass_days=0,
                        product_type="redeem",
                        pay_currency="redeem",
                        redeem_price=int(item["redeem_price"]),
                        grant_payload=validate_grant_payload(item.get("grant_payload")),
                        per_user_limit=int(item.get("per_user_limit") or 0),
                        stock_total=stock_total,
                        stock_sold=0,
                        sort_order=int(item.get("sort_order") or 0),
                        featured=bool(item.get("featured", False)),
                        active=True,
                        updated_at=_utcnow(),
                    )
                )
                created += 1
        deactivated = 0
        if deactivate_missing:
            orphans = (
                self.db.query(Product)
                .filter(Product.pay_currency == "redeem", Product.sku.notin_(seen_skus))
                .all()
            )
            for p in orphans:
                p.active = False
                deactivated += 1
        self.db.commit()
        return {
            "status": "ok",
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
            "skus": sorted(seen_skus),
            "total_in_catalog": len(REDEEM_PRODUCTS),
        }
