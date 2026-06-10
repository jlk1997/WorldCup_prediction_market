"""Tests for auth and commerce APIs."""

import hashlib

import pytest
from sqlalchemy.orm import Session

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
    from datetime import datetime, timedelta, timezone

    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.add(
        AuthCode(
            email=email,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=expires,
        )
    )
    db.commit()


def test_send_code_dev_mode(client):
    resp = client.post(
        "/api/auth/send-code",
        json={"email": "test@example.com", "age_confirmed": True},
    )
    assert resp.status_code == 200


def test_send_code_requires_age(client):
    resp = client.post(
        "/api/auth/send-code",
        json={"email": "test@example.com", "age_confirmed": False},
    )
    assert resp.status_code == 400


def test_verify_and_me(client, db: Session):
    email = "verify_test@example.com"
    _seed_auth_code(db, email)
    resp = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["fan_coins"] >= 100

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_shop_products(client, db: Session):
    if not db.query(Product).first():
        db.add(
            Product(
                sku="test_pack",
                name="测试包",
                price_fen=600,
                coins_grant=60,
                grant_season_pass_days=0,
                product_type="coins",
                active=True,
                sort_order=1,
            )
        )
        db.commit()
    resp = client.get("/api/shop/products")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_mock_pay_flow(client, db: Session):
    email = "pay_test@example.com"
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
            sku="mock_pack",
            name="Mock",
            price_fen=100,
            coins_grant=50,
            grant_season_pass_days=0,
            product_type="coins",
            active=True,
            sort_order=0,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    create = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    )
    assert create.status_code == 200
    order = create.json()["order"]
    mock = client.post(
        f"/api/pay/alipay/mock-pay?out_trade_no={order['out_trade_no']}",
        headers=headers,
    )
    assert mock.status_code == 200
    assert mock.json()["status"] == "paid"
    assert mock.json()["product_name"] == product.name
    assert mock.json()["coins_grant"] == product.coins_grant

    detail = client.get(
        f"/api/pay/orders/by-no/{order['out_trade_no']}",
        headers=headers,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "paid"
    assert body["product_name"] == product.name
    assert body["out_trade_no"] == order["out_trade_no"]

    # 幂等：重复 mock 不应重复发币
    user = db.get(User, login["user"]["id"])
    assert user.fan_coins >= login["user"]["fan_coins"] + product.coins_grant
    coins_after_first = user.fan_coins
    mock2 = client.post(
        f"/api/pay/alipay/mock-pay?out_trade_no={order['out_trade_no']}",
        headers=headers,
    )
    assert mock2.status_code == 200
    db.refresh(user)
    assert user.fan_coins == coins_after_first


def test_raise_predict_stake(client, db: Session):
    email = "raise_test@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user = db.get(User, login["user"]["id"])
    user.profile_completed = True
    user.fan_coins = 500
    db.commit()

    from app.db.models import Match

    match = db.query(Match).first()
    if not match:
        pytest.skip("no matches in test db")

    pred = client.post(
        "/api/game/predict",
        json={"match_id": match.id, "pick": "home", "stake_coins": 50, "use_free": False},
        headers=headers,
    )
    assert pred.status_code == 200

    raise_resp = client.post(
        "/api/game/predict/raise-stake",
        json={"match_id": match.id, "additional_stake_coins": 30},
        headers=headers,
    )
    assert raise_resp.status_code == 200
    assert raise_resp.json()["stake_coins"] == 80

    dup = client.post(
        "/api/game/predict",
        json={"match_id": match.id, "pick": "draw", "stake_coins": 10, "use_free": False},
        headers=headers,
    )
    assert dup.status_code == 400
    assert "已竞猜" in dup.json()["message"]


def _pay_product(client, db: Session, headers: dict, product: Product) -> dict:
    create = client.post(
        "/api/pay/alipay/create",
        json={"product_id": product.id, "age_confirmed": True},
        headers=headers,
    )
    assert create.status_code == 200
    order = create.json()["order"]
    mock = client.post(
        f"/api/pay/alipay/mock-pay?out_trade_no={order['out_trade_no']}",
        headers=headers,
    )
    assert mock.status_code == 200
    return mock.json()


def test_mock_pay_team_cosmetic(client, db: Session):
    email = "cosmetic_test@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    product = db.query(Product).filter(Product.sku == "team_cosmetic").first()
    if not product:
        product = Product(
            sku="team_cosmetic",
            name="主队装扮包",
            price_fen=1200,
            coins_grant=50,
            grant_season_pass_days=0,
            product_type="cosmetic",
            grant_payload={"avatar_frame": "gold_wc", "theme_key": "team_spirit"},
            active=True,
            sort_order=5,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    body = _pay_product(client, db, headers, product)
    assert body["product_type"] == "cosmetic"
    assert "头像金框" in body["grant_summary"]
    assert "全站主题色" in body["grant_summary"]

    me = client.get("/api/auth/me", headers=headers).json()
    assert me["avatar_frame"] == "gold_wc"
    assert me["theme_key"] == "team_spirit"


def test_mock_pay_season_pass(client, db: Session):
    email = "pass_test@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    product = db.query(Product).filter(Product.sku == "season_pass").first()
    if not product:
        product = Product(
            sku="season_pass",
            name="赛季竞猜通行证",
            price_fen=6800,
            coins_grant=0,
            grant_season_pass_days=30,
            product_type="season_pass",
            active=True,
            sort_order=4,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    body = _pay_product(client, db, headers, product)
    assert body["grant_season_pass_days"] == 30
    assert any("通行证" in s for s in body["grant_summary"])

    me = client.get("/api/auth/me", headers=headers).json()
    assert me["has_season_pass"] is True
    assert me["has_active_season_pass"] is True
    assert me["season_pass_until"] is not None
