"""Commerce hardening: pending order reuse, nickname change."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import Product, User
from app.db.session import SessionLocal
from app.db.repositories.user_repository import UserRepository
from app.services.payment_service import PaymentService


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


def test_pending_order_reused(client, db: Session):
    email = f"pending_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    product = db.query(Product).filter(Product.active.is_(True)).first()
    assert product

    first = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    ).json()
    second = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    ).json()
    assert first["order"]["out_trade_no"] == second["order"]["out_trade_no"]


def test_nickname_change_costs_coins(db: Session):
    user = User(email=f"nick_{uuid.uuid4().hex[:10]}@example.com", nickname="old", fan_coins=100)
    db.add(user)
    db.commit()
    db.refresh(user)
    settings = get_settings()
    updated = UserRepository(db).change_nickname(user, "new_name")
    assert updated.nickname == "new_name"
    assert updated.fan_coins == 100 - settings.nickname_change_cost


def test_list_orders(client, db: Session):
    email = f"orders_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    product = db.query(Product).filter(Product.active.is_(True)).first()
    client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    )
    resp = client.get("/api/pay/orders", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
