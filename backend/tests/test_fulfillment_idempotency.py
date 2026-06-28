"""Idempotency and concurrency guards for paid order fulfillment."""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import Order, Product, User
from app.db.session import SessionLocal
from app.services.mint_bundle_service import MintBundleService
from app.services.payment_service import PaymentService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_mint_bundle_grant_idempotent(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"bundle_{suffix}@test.com", nickname=f"b_{suffix}")
    db.add(user)
    db.flush()
    product = Product(
        sku=f"mint_bundle_test_{suffix}",
        name="测试组合包",
        product_type="mint_bundle",
        price_fen=9900,
        pay_currency="cash",
        active=True,
        grant_payload={"ai_live_credits": 1},
    )
    db.add(product)
    db.flush()
    order = Order(
        out_trade_no=f"TEST{suffix}",
        user_id=user.id,
        product_id=product.id,
        amount_fen=9900,
        status="paid",
        grant_result_json={"product_type": "mint_bundle", "sku": product.sku, "ai_live_credits": 1},
    )
    db.add(order)
    db.commit()

    before_live = getattr(user, "ai_pack_live_credits", 0) or 0
    result = MintBundleService(db).grant(user, product, order)
    db.commit()
    db.refresh(user)

    assert result["product_type"] == "mint_bundle"
    assert (getattr(user, "ai_pack_live_credits", 0) or 0) == before_live


def test_fulfill_order_skips_when_grant_result_present(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"paid_{suffix}@test.com", nickname=f"p_{suffix}", fan_coins=100)
    db.add(user)
    db.flush()
    product = Product(
        sku=f"coins_pack_{suffix}",
        name="球迷币包",
        product_type="coins_pack",
        price_fen=100,
        pay_currency="cash",
        active=True,
        coins_grant=50,
    )
    db.add(product)
    db.flush()
    order = Order(
        out_trade_no=f"PAID{suffix}",
        user_id=user.id,
        product_id=product.id,
        amount_fen=100,
        status="paid",
        grant_result_json={"product_type": "coins_pack", "coins_grant": 50},
    )
    db.add(order)
    db.commit()

    svc = PaymentService(db)
    svc.wallet = MagicMock()

    svc._fulfill_order(order, alipay_trade_no="TRADE123")
    svc.wallet.add_coins.assert_not_called()


def test_buyer_ai_note_near_floor():
    from app.services.marketplace_service import MarketplaceService

    note = MarketplaceService._buyer_ai_note(100, floor=100, est=120, active_listings=3)
    assert "地板" in note
