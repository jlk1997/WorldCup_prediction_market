"""Season pass daily grant tests."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import Product, User
from app.db.session import SessionLocal
from app.services.payment_service import PaymentService
from app.services.season_pass_service import SeasonPassService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_auth_code(db: Session, email: str, code: str = "123456") -> None:
    from app.db.models.commerce import AuthCode

    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.add(
        AuthCode(
            email=email,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=expires,
        )
    )
    db.commit()


def test_season_pass_daily_grant(client, db: Session):
    email = f"pass_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    user = db.get(User, login["user"]["id"])
    user.has_season_pass = True
    user.season_pass_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    db.commit()

    me1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"}).json()
    settings = get_settings()
    assert me1["fan_coins"] >= login["user"]["fan_coins"] + settings.season_pass_daily_coins

    me2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"}).json()
    assert me2["fan_coins"] == me1["fan_coins"]


def test_season_pass_daily_claim_endpoint(client, db: Session):
    email = f"passclaim_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    user = db.get(User, login["user"]["id"])
    user.has_season_pass = True
    user.season_pass_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    user.last_season_pass_daily = None
    db.commit()

    headers = {"Authorization": f"Bearer {login['access_token']}"}
    r = client.post("/api/game/season-pass/daily-claim", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("granted", 0) > 0


def test_create_order_requires_age(client, db: Session):
    email = f"pay_age_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    product = db.query(Product).filter(Product.active.is_(True)).first()
    if not product:
        product = Product(
            sku=f"test_{uuid.uuid4().hex[:6]}",
            name="Test",
            price_fen=100,
            coins_grant=10,
            grant_season_pass_days=0,
            product_type="coins",
            active=True,
            sort_order=99,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    bad = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": False},
        headers=headers,
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    )
    assert ok.status_code == 200


def test_payment_amount_missing_rejected(db: Session):
    svc = PaymentService(db)
    from app.db.models.commerce import Order

    order = Order(
        out_trade_no=f"T{uuid.uuid4().hex[:8]}",
        user_id=1,
        product_id=1,
        amount_fen=6800,
        status="pending",
    )
    assert svc._amount_matches_order(order, {}) is False


def test_grant_daily_batch(db: Session):
    user = User(
        email=f"batch_{uuid.uuid4().hex[:10]}@example.com",
        nickname="batch",
        fan_coins=0,
        has_season_pass=True,
        season_pass_until=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=10),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    result = SeasonPassService(db).grant_daily_batch()
    assert result["granted_users"] >= 1
