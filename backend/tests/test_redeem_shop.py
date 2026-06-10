"""Tests for points redemption shop."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import Product, User
from app.db.repositories.user_repository import WalletRepository
from app.db.session import SessionLocal
from app.services.redeem_shop_service import RedeemShopService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_user(db: Session, email: str | None = None, redeem_points: int = 1000) -> User:
    email = email or f"redeem_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, nickname=email.split("@")[0], fan_coins=100, redeem_points=redeem_points)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_redeem_product(db: Session, sku: str | None = None, price: int = 100) -> Product:
    sku = sku or f"test_redeem_{uuid.uuid4().hex[:8]}"
    p = Product(
        sku=sku,
        name="测试兑换",
        price_fen=0,
        coins_grant=0,
        product_type="redeem",
        pay_currency="redeem",
        redeem_price=price,
        grant_payload={"badge_code": "test_badge", "badge_title": "测试徽章"},
        per_user_limit=1,
        stock_total=2,
        stock_sold=0,
        active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_redeem_purchase_success(db: Session):
    user = _seed_user(db, redeem_points=500)
    product = _seed_redeem_product(db, price=200)
    svc = RedeemShopService(db)
    result = svc.purchase(user.id, product.id, idempotency_key="idem-1")
    assert result["order"].status == "completed"
    assert result["redeem_points_after"] == 300
    db.refresh(product)
    assert product.stock_sold == 1


def test_redeem_insufficient_points(db: Session):
    user = _seed_user(db, redeem_points=50)
    product = _seed_redeem_product(db, price=200)
    svc = RedeemShopService(db)
    with pytest.raises(Exception):
        svc.purchase(user.id, product.id)


def test_redeem_idempotent_replay(db: Session):
    user = _seed_user(db, redeem_points=500)
    product = _seed_redeem_product(db, price=100)
    svc = RedeemShopService(db)
    first = svc.purchase(user.id, product.id, idempotency_key="same-key")
    second = svc.purchase(user.id, product.id, idempotency_key="same-key")
    assert first["order"].id == second["order"].id
    assert second.get("idempotent_replay") is True
    db.refresh(user)
    assert user.redeem_points == 400


def test_redeem_per_user_limit(db: Session):
    user = _seed_user(db, redeem_points=1000)
    product = _seed_redeem_product(db, price=50)
    svc = RedeemShopService(db)
    svc.purchase(user.id, product.id, idempotency_key="a")
    with pytest.raises(Exception):
        svc.purchase(user.id, product.id, idempotency_key="b")


def test_redeem_admin_refund(db: Session):
    user = _seed_user(db, redeem_points=500)
    product = _seed_redeem_product(db, price=200)
    svc = RedeemShopService(db)
    result = svc.purchase(user.id, product.id, idempotency_key="refund-test")
    order_id = result["order"].id
    db.refresh(user)
    assert user.redeem_points == 300
    refund = svc.admin_refund_order(order_id)
    assert refund["status"] == "refunded"
    db.refresh(user)
    db.refresh(product)
    assert user.redeem_points == 500
    assert product.stock_sold == 0


def test_wallet_ledger_dedup(db: Session):
    user = _seed_user(db, redeem_points=0)
    wallet = WalletRepository(db)
    wallet.add_redeem_points(user, 50, "predict_win_redeem", "game_prediction", 999001)
    wallet.add_redeem_points(user, 50, "predict_win_redeem", "game_prediction", 999001)
    db.commit()
    db.refresh(user)
    assert user.redeem_points == 50
    rows = wallet.list_point_ledger(user.id, bucket="redeem")
    assert sum(1 for r in rows if r["ref_id"] == 999001 and r["reason"] == "predict_win_redeem") == 1


def test_redeem_api(client, db: Session):
    from app.services.product_catalog_service import ProductCatalogService

    ProductCatalogService(db).sync_redeem_catalog()
    email = f"redeem_api_{uuid.uuid4().hex[:8]}@test.com"
    from app.db.models.commerce import AuthCode

    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.add(
        AuthCode(
            email=email,
            code_hash=hashlib.sha256(b"123456").hexdigest(),
            expires_at=expires,
        )
    )
    db.commit()
    resp = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    user = db.query(User).filter(User.email == email).first()
    user.redeem_points = 2000
    db.commit()
    products = client.get("/api/shop/redeem/products")
    assert products.status_code == 200
    assert len(products.json()) >= 1
    purchasable = next((p for p in products.json() if p.get("can_purchase")), products.json()[0])
    pid = purchasable["id"]
    buy = client.post(
        "/api/shop/redeem/purchase",
        json={"product_id": pid, "idempotency_key": "api-test-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert buy.status_code == 200
    assert buy.json()["order"]["status"] == "completed"
