"""Admin CRUD for redeem shop products."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import AuthCode, Product, User
from app.db.session import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_auth_code(db: Session, email: str, code: str = "123456") -> None:
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.add(
        AuthCode(
            email=email,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=expires,
        )
    )
    db.commit()


def _login(client, db: Session, email: str) -> str:
    _seed_auth_code(db, email)
    resp = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _admin_headers(monkeypatch) -> dict:
    monkeypatch.setenv("PRODUCTION_MODE", "true")
    monkeypatch.setenv("ADMIN_SYNC_SECRET", "test-admin-secret")
    get_settings.cache_clear()
    return {"X-Admin-Secret": "test-admin-secret"}


def _seed_redeem(db: Session, sku: str, price: int = 100) -> Product:
    p = Product(
        sku=sku,
        name=f"Test {sku}",
        description="test",
        price_fen=0,
        coins_grant=0,
        grant_season_pass_days=0,
        product_type="redeem",
        pay_currency="redeem",
        redeem_price=price,
        grant_payload={"badge_code": "test_badge", "badge_title": "Test"},
        per_user_limit=0,
        stock_total=0,
        stock_sold=0,
        active=True,
        sort_order=0,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_admin_redeem_requires_secret_in_production(client, monkeypatch):
    monkeypatch.setenv("PRODUCTION_MODE", "true")
    monkeypatch.setenv("ADMIN_SYNC_SECRET", "test-admin-secret")
    get_settings.cache_clear()
    resp = client.get("/api/shop/admin/redeem/products")
    assert resp.status_code == 401
    get_settings.cache_clear()


def test_admin_redeem_crud_and_public_list(client, db: Session, monkeypatch):
    headers = _admin_headers(monkeypatch)
    sku = f"admin_crud_{uuid.uuid4().hex[:8]}"

    create = client.post(
        "/api/shop/admin/redeem/products",
        headers=headers,
        json={
            "sku": sku,
            "name": "管理测试商品",
            "description": "desc",
            "redeem_price": 150,
            "grant_payload": {"avatar_frame": "silver_wc"},
            "per_user_limit": 1,
            "stock_total": 10,
            "sort_order": 1,
            "featured": True,
        },
    )
    assert create.status_code == 200
    product_id = create.json()["id"]
    assert create.json()["redeem_price"] == 150
    assert create.json()["featured"] is True

    patch = client.patch(
        f"/api/shop/admin/redeem/products/{product_id}",
        headers=headers,
        json={"redeem_price": 280},
    )
    assert patch.status_code == 200
    assert patch.json()["redeem_price"] == 280

    public = client.get("/api/shop/redeem/products")
    assert public.status_code == 200
    match = next(p for p in public.json() if p["sku"] == sku)
    assert match["redeem_price"] == 280

    toggle = client.post(
        f"/api/shop/admin/redeem/products/{product_id}/toggle",
        headers=headers,
    )
    assert toggle.status_code == 200
    assert toggle.json()["active"] is False

    public2 = client.get("/api/shop/redeem/products")
    assert all(p["sku"] != sku for p in public2.json())
    get_settings.cache_clear()


def test_admin_invalid_grant_payload(client, monkeypatch):
    headers = _admin_headers(monkeypatch)
    resp = client.post(
        "/api/shop/admin/redeem/products",
        headers=headers,
        json={
            "sku": f"bad_{uuid.uuid4().hex[:6]}",
            "name": "Bad",
            "redeem_price": 100,
            "grant_payload": {"unknown_field": "x"},
        },
    )
    assert resp.status_code == 400
    get_settings.cache_clear()


def test_admin_stock_total_below_sold(client, db: Session, monkeypatch):
    headers = _admin_headers(monkeypatch)
    p = _seed_redeem(db, f"stock_{uuid.uuid4().hex[:6]}", 100)
    p.stock_total = 50
    p.stock_sold = 30
    db.commit()

    resp = client.patch(
        f"/api/shop/admin/redeem/products/{p.id}",
        headers=headers,
        json={"stock_total": 20},
    )
    assert resp.status_code == 400
    get_settings.cache_clear()


def test_redeem_rules_catalog_source_db(client, db: Session):
    _seed_redeem(db, f"rules_{uuid.uuid4().hex[:6]}", 50)
    resp = client.get("/api/shop/redeem/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["catalog_source"] == "database:products"
    assert "grant_payload_schema" in body


def test_daily_status_redeem_progress_from_db(client, db: Session):
    email = f"redeem_prog_{uuid.uuid4().hex[:8]}@example.com"
    token = _login(client, db, email)
    headers = {"Authorization": f"Bearer {token}"}
    db.query(Product).filter(Product.pay_currency == "redeem").update(
        {Product.active: False}, synchronize_session=False
    )
    sku = f"prog_{uuid.uuid4().hex[:8]}"
    product = _seed_redeem(db, sku, 500)
    product.active = True
    db.commit()

    user = db.query(User).filter(User.email == email).first()
    user.redeem_points = 200
    db.commit()

    status = client.get("/api/game/daily-status", headers=headers).json()
    progress = status.get("redeem_progress")
    assert progress is not None
    assert progress["next_sku"] == sku
    assert progress["gap"] == 300
