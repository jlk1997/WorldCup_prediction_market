"""人民币打新 + 支付宝订单 E2E 测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, MintEvent, MintReservation, User
from app.db.session import SessionLocal
from app.services.payment_service import PaymentService
from app.services.primary_mint_service import PrimaryMintService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user(db: Session, email: str = "rmb_mint@test.com") -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            nickname="MintTester",
            fan_coins=1000,
            real_name_verified=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _card(db: Session) -> CollectibleCard:
    c = db.query(CollectibleCard).filter(CollectibleCard.active.is_(True)).first()
    if not c:
        c = CollectibleCard(
            code="test_mint_card",
            name="测试球星",
            rarity="epic",
            series="legend",
            active=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
    return c


def _rmb_event(db: Session, *, total: int = 5, issued: int = 0, user: User | None = None) -> MintEvent:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    suffix = int(now.timestamp() * 1000)
    card = CollectibleCard(
        code=f"test_mint_card_{suffix}",
        name="测试球星",
        rarity="epic",
        series="legend",
        active=True,
    )
    db.add(card)
    db.flush()
    code = f"test_rmb_{suffix}"
    ev = MintEvent(
        code=code,
        name="测试人民币打新",
        card_code=card.code,
        total_supply=total,
        issued=issued,
        currency="rmb",
        price_fen=100,
        price_coins=0,
        per_user_limit=1,
        sale_mode="public",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(days=1),
        status="live",
        active=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def test_rmb_mint_create_order_and_fulfill(db: Session):
    user = _user(db)
    event = _rmb_event(db)
    mint_svc = PrimaryMintService(db)
    order, pay_url, channel = mint_svc.create_rmb_order(user, event.id)
    assert order.status == "pending"
    assert order.mint_event_id == event.id
    assert "mock=1" in pay_url or pay_url.startswith("http")
    assert channel in ("page", "wap")

    pay_svc = PaymentService(db)
    paid = pay_svc.mock_pay_success(order.out_trade_no, user.id)
    assert paid.status == "paid"
    assert paid.grant_result_json
    assert paid.grant_result_json.get("serial_no") is not None

    db.refresh(event)
    assert event.issued == 1


def test_rmb_mint_inventory_lock(db: Session):
    from app.core.exceptions import BadRequestError

    user = _user(db, "lock_a@test.com")
    user_b = _user(db, "lock_b@test.com")
    event = _rmb_event(db, total=1)
    mint_svc = PrimaryMintService(db)
    mint_svc.create_rmb_order(user, event.id)

    with pytest.raises(BadRequestError):
        mint_svc.create_rmb_order(user_b, event.id)


def test_rmb_mint_expire_releases_lock(db: Session):
    user = _user(db, "expire@test.com")
    event = _rmb_event(db, total=2)
    mint_svc = PrimaryMintService(db)
    order, _, _ = mint_svc.create_rmb_order(user, event.id)
    res = (
        db.query(MintReservation)
        .filter(MintReservation.pending_order_id == order.id)
        .first()
    )
    assert res is not None
    res.lock_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()

    result = mint_svc.expire_pending_mint_orders()
    assert result["expired"] >= 1
    db.refresh(order)
    assert order.status == "cancelled"
    assert mint_svc.available_supply(event) >= 1


def test_rmb_mint_fulfill_idempotent(db: Session):
    user = _user(db, "idem@test.com")
    event = _rmb_event(db, total=3, issued=0)
    mint_svc = PrimaryMintService(db)
    order, _, _ = mint_svc.create_rmb_order(user, event.id)
    pay_svc = PaymentService(db)
    pay_svc.mock_pay_success(order.out_trade_no, user.id)
    serial_first = order.grant_result_json.get("serial_no")
    pay_svc.mock_pay_success(order.out_trade_no, user.id)
    assert order.grant_result_json.get("serial_no") == serial_first


def test_rmb_mint_api(client, db: Session):
    import hashlib
    import uuid
    from app.db.models.commerce import AuthCode

    email = f"api_mint_{uuid.uuid4().hex[:8]}@test.com"
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.add(
        AuthCode(
            email=email,
            code_hash=hashlib.sha256(b"123456").hexdigest(),
            expires_at=expires,
        )
    )
    db.commit()
    _user(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    event = _rmb_event(db)

    resp = client.post(
        f"/api/mint-events/{event.id}/create-order",
        json={"age_confirmed": True, "pay_channel": "page"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order"]["status"] == "pending"
    assert body["pay_url"]

    mock = client.post(
        f"/api/pay/alipay/mock-pay?out_trade_no={body['order']['out_trade_no']}",
        headers=headers,
    )
    assert mock.status_code == 200
    detail = mock.json()
    assert detail["status"] == "paid"
    assert detail.get("mint_serial_no") is not None
