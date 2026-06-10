"""Dual points ledger and redeem shop tests."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.db.models.commerce import AuthCode, PointLedger, Product, RedeemOrder, User
from app.db.repositories.user_repository import WalletRepository
from app.db.session import SessionLocal
from app.services.leaderboard_service import LeaderboardService
from app.services.redeem_shop_service import RedeemShopService


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


def _login(client, db: Session) -> tuple[str, User]:
    email = f"dual_{uuid.uuid4().hex[:10]}@example.com"
    _seed_auth_code(db, email)
    body = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    user = db.get(User, body["user"]["id"])
    return body["access_token"], user


def _redeem_product(
    db: Session,
    sku: str,
    price: int,
    payload: dict,
    limit: int = 0,
    stock_total: int = 0,
) -> Product:
    existing = db.query(Product).filter(Product.sku == sku).first()
    if existing:
        existing.stock_total = stock_total
        db.commit()
        db.refresh(existing)
        return existing
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
        grant_payload=payload,
        per_user_limit=limit,
        stock_total=stock_total,
        stock_sold=0,
        active=True,
        sort_order=200,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_wallet_dual_ledger(db: Session):
    user = User(email=f"w_{uuid.uuid4().hex[:8]}@t.com", nickname="w", fan_coins=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    wallet = WalletRepository(db)

    wallet.add_season_points(user, 100, "test_season", "user", user.id)
    wallet.add_redeem_points(user, 50, "test_redeem", "user", user.id)
    db.commit()
    db.refresh(user)

    assert user.season_points == 100
    assert user.redeem_points == 50

    wallet.deduct_redeem_points(user, 20, "redeem_test", "user", user.id)
    db.commit()
    db.refresh(user)

    assert user.redeem_points == 30
    assert user.season_points == 100

    season_rows = db.query(PointLedger).filter(PointLedger.user_id == user.id, PointLedger.point_bucket == "season").count()
    redeem_rows = db.query(PointLedger).filter(PointLedger.user_id == user.id, PointLedger.point_bucket == "redeem").count()
    assert season_rows == 1
    assert redeem_rows == 2


def test_deduct_redeem_insufficient(db: Session):
    user = User(email=f"ins_{uuid.uuid4().hex[:8]}@t.com", nickname="x", fan_coins=0, redeem_points=5)
    db.add(user)
    db.commit()
    db.refresh(user)
    wallet = WalletRepository(db)
    with pytest.raises(BadRequestError, match="可用积分不足"):
        wallet.deduct_redeem_points(user, 10, "x", None, None)


def test_redeem_shop_purchase(client, db: Session):
    token, user = _login(client, db)
    headers = {"Authorization": f"Bearer {token}"}
    product = _redeem_product(
        db,
        f"test_badge_{uuid.uuid4().hex[:6]}",
        100,
        {"badge_code": "test_badge", "badge_title": "测试徽章"},
        limit=1,
    )
    user.redeem_points = 200
    db.commit()

    resp = client.post("/api/shop/redeem/purchase", json={"product_id": product.id}, headers=headers)
    assert resp.status_code == 200
    db.refresh(user)
    assert user.redeem_points == 100

    resp2 = client.post("/api/shop/redeem/purchase", json={"product_id": product.id}, headers=headers)
    assert resp2.status_code == 400


def test_cash_shop_excludes_redeem_products(client, db: Session):
    _redeem_product(db, f"cash_ex_{uuid.uuid4().hex[:6]}", 50, {"badge_code": "x"})
    cash = db.query(Product).filter(Product.pay_currency == "cash", Product.active.is_(True)).first()
    if not cash:
        db.add(
            Product(
                sku=f"cash_{uuid.uuid4().hex[:6]}",
                name="Cash",
                price_fen=100,
                coins_grant=10,
                product_type="coins",
                pay_currency="cash",
                active=True,
                sort_order=1,
            )
        )
        db.commit()

    resp = client.get("/api/shop/products")
    assert resp.status_code == 200
    for p in resp.json():
        assert p.get("pay_currency", "cash") != "redeem"


def test_redeem_products_list(client, db: Session):
    _redeem_product(db, f"list_{uuid.uuid4().hex[:6]}", 80, {"theme_key": "team_spirit"})
    resp = client.get("/api/shop/redeem/products")
    assert resp.status_code == 200
    assert any(p["pay_currency"] == "redeem" for p in resp.json())


def test_leaderboard_redeem_board(db: Session):
    u1 = User(email=f"lb1_{uuid.uuid4().hex[:6]}@t.com", nickname="A", redeem_points=500)
    u2 = User(email=f"lb2_{uuid.uuid4().hex[:6]}@t.com", nickname="B", redeem_points=300)
    db.add_all([u1, u2])
    db.commit()
    svc = LeaderboardService(db)
    board = svc.get_redeem_points_board("season", limit=500)
    assert board["board"] == "redeem_points"
    by_id = {r["user_id"]: r for r in board["rows"]}
    assert u1.id in by_id and u2.id in by_id
    assert by_id[u1.id]["redeem_points"] == 500
    assert by_id[u2.id]["redeem_points"] == 300


def test_leaderboard_points_filters_season_bucket(db: Session):
    user = User(email=f"pts_{uuid.uuid4().hex[:6]}@t.com", nickname="C", season_points=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    wallet = WalletRepository(db)
    wallet.add_season_points(user, 40, "predict_win", "game_prediction", 1)
    wallet.add_redeem_points(user, 20, "predict_win_redeem", "game_prediction", 1)
    db.commit()

    svc = LeaderboardService(db)
    season_board = svc.get_points_board("season", limit=500)
    redeem_board = svc.get_redeem_points_board("season", limit=500)
    season_ids = {r["user_id"] for r in season_board["rows"]}
    redeem_ids = {r["user_id"] for r in redeem_board["rows"]}
    assert user.id in season_ids
    assert user.id in redeem_ids
    season_row = next(r for r in season_board["rows"] if r["user_id"] == user.id)
    redeem_row = next(r for r in redeem_board["rows"] if r["user_id"] == user.id)
    assert season_row["season_points"] == 40
    assert redeem_row["redeem_points"] == 20


def test_my_summary_includes_redeem(client, db: Session):
    token, user = _login(client, db)
    user.redeem_points = 120
    user.season_points = 300
    db.commit()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/game/leaderboard/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["redeem_points"] == 120
    assert body["season_points"] == 300
    assert "redeem_rank" in body


def test_catalog_sync_upsert(db: Session):
    from app.services.product_catalog_service import ProductCatalogService

    svc = ProductCatalogService(db)
    r1 = svc.sync_redeem_catalog()
    assert r1["total_in_catalog"] >= 4
    r2 = svc.sync_redeem_catalog()
    assert r2["updated"] >= 1 or r2["created"] == 0


def test_redeem_rules_includes_schema(client, db: Session):
    resp = client.get("/api/shop/redeem/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert "grant_payload_schema" in body
    assert "avatar_frame" in body["grant_payload_schema"]
    assert body.get("catalog_source")


def test_redeem_products_enriched(client, db: Session):
    token, user = _login(client, db)
    headers = {"Authorization": f"Bearer {token}"}
    product = _redeem_product(
        db,
        f"enriched_{uuid.uuid4().hex[:6]}",
        50,
        {"badge_code": "t", "badge_title": "T"},
        limit=1,
    )
    user.redeem_points = 10
    db.commit()
    resp = client.get("/api/shop/redeem/products", headers=headers)
    assert resp.status_code == 200
    row = next(p for p in resp.json() if p["id"] == product.id)
    assert row["purchase_blocked_reason"] == "insufficient_points"
    assert row["can_purchase"] is False


def test_redeem_rules(client, db: Session):
    _redeem_product(db, f"rules_{uuid.uuid4().hex[:6]}", 50, {"badge_code": "x", "badge_title": "X"})
    resp = client.get("/api/shop/redeem/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert "economy" in body
    assert body["economy"]["predict_win_redeem_ratio"] == get_settings().predict_win_redeem_ratio


def test_point_ledger_api(client, db: Session):
    token, user = _login(client, db)
    headers = {"Authorization": f"Bearer {token}"}
    WalletRepository(db).add_redeem_points(user, 80, "test", "user", user.id)
    db.commit()
    resp = client.get("/api/wallet/point-ledger?bucket=redeem", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(r["delta"] == 80 for r in data)


def test_prediction_card_includes_redeem_field(client, db: Session):
    token, _user = _login(client, db)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/game/my-predictions", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    for row in rows:
        assert "redeem_points_awarded" in row


def test_extra_free_predict_grant(client, db: Session):
    token, user = _login(client, db)
    headers = {"Authorization": f"Bearer {token}"}
    product = _redeem_product(
        db,
        f"extra_fp_{uuid.uuid4().hex[:6]}",
        10,
        {"extra_free_predict_daily": 2},
        limit=0,
        stock_total=0,
    )
    user.redeem_points = 100
    db.commit()

    resp = client.post("/api/shop/redeem/purchase", json={"product_id": product.id}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["redeem_points_after"] == 90
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["extra_free_predict_daily"] == 2


def test_global_stock_limit(client, db: Session):
    token1, user1 = _login(client, db)
    token2, user2 = _login(client, db)
    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}
    product = _redeem_product(
        db,
        f"stock_{uuid.uuid4().hex[:6]}",
        10,
        {"badge_code": "limited", "badge_title": "限量"},
        limit=0,
        stock_total=1,
    )
    user1.redeem_points = 100
    user2.redeem_points = 100
    db.commit()

    ok = client.post("/api/shop/redeem/purchase", json={"product_id": product.id}, headers=h1)
    assert ok.status_code == 200
    assert ok.json()["stock_remaining"] == 0

    list_resp = client.get("/api/shop/redeem/products", headers=h2)
    row = next(p for p in list_resp.json() if p["id"] == product.id)
    assert row["is_out_of_stock"] is True
    assert row["purchase_blocked_reason"] == "out_of_stock"

    fail = client.post("/api/shop/redeem/purchase", json={"product_id": product.id}, headers=h2)
    assert fail.status_code == 400
