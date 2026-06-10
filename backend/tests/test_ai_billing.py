"""AI billing: free quota, coin deduction, cache preview, API auth."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.db.models.commerce import AiUsageDaily, User
from app.db.session import SessionLocal
from app.services.ai_billing_service import AiBillingService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_user(db: Session, fan_coins: int = 100) -> User:
    email = f"ai_{uuid.uuid4().hex[:12]}@example.com"
    user = User(email=email, nickname="tester", fan_coins=fan_coins)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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


def test_preview_cache_hit_no_charge(db: Session):
    user = _make_user(db)
    svc = AiBillingService(db)
    decision = svc.preview(user, "pre_match", False, cache_hit=True)
    assert decision.charge_coins == 0
    assert not decision.used_free_quota


def test_free_quota_then_coin_charge(db: Session):
    settings = get_settings()
    user = _make_user(db, fan_coins=200)
    svc = AiBillingService(db)

    for _ in range(settings.ai_daily_free_analyses):
        d = svc.charge_before_llm(user.id, "pre_match", False)
        assert d.charge_coins == 0
        assert d.used_free_quota
    db.commit()
    db.refresh(user)

    d = svc.charge_before_llm(user.id, "pre_match", False)
    assert d.charge_coins == settings.ai_coin_cost_pre_match
    assert not d.used_free_quota
    db.commit()
    db.refresh(user)
    assert user.fan_coins == 200 - settings.ai_coin_cost_pre_match


def test_insufficient_coins_raises(db: Session):
    settings = get_settings()
    user = _make_user(db, fan_coins=0)
    svc = AiBillingService(db)
    for _ in range(settings.ai_daily_free_analyses):
        svc.charge_before_llm(user.id, "pre_match", False)
    db.commit()
    with pytest.raises(BadRequestError):
        svc.charge_before_llm(user.id, "pre_match", False)


def test_refund_restores_coins(db: Session):
    settings = get_settings()
    user = _make_user(db, fan_coins=200)
    svc = AiBillingService(db)
    for _ in range(settings.ai_daily_free_analyses):
        svc.charge_before_llm(user.id, "pre_match", False)
    d = svc.charge_before_llm(user.id, "pre_match", False)
    db.commit()
    db.refresh(user)
    after = user.fan_coins
    svc.refund(user.id, d.charge_coins)
    db.commit()
    db.refresh(user)
    assert user.fan_coins == after + d.charge_coins


def test_season_pass_extra_free_quota(db: Session):
    settings = get_settings()
    user = _make_user(db, fan_coins=100)
    user.has_season_pass = True
    user.season_pass_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    db.commit()
    svc = AiBillingService(db)
    limit = svc.daily_free_limit(user)
    assert limit == settings.ai_daily_free_analyses + settings.season_pass_extra_ai_free


def test_agent_analyze_requires_auth(client):
    resp = client.post(
        "/api/agent/analyze",
        json={"team1_name": "Brazil", "team2_name": "Argentina", "mode": "pre_match", "force_refresh": False},
    )
    assert resp.status_code == 401


def test_predict_analysis_deprecated(client):
    resp = client.post("/api/predict/analysis", json={"team1_name": "A", "team2_name": "B"})
    assert resp.status_code == 410


def test_refund_free_quota(db: Session):
    user = _make_user(db, fan_coins=100)
    svc = AiBillingService(db)
    d = svc.charge_before_llm(user.id, "pre_match", False)
    assert d.used_free_quota
    db.commit()
    row = db.query(AiUsageDaily).filter(AiUsageDaily.user_id == user.id).first()
    assert row and row.free_used == 1
    svc.refund_charge(user.id, d)
    db.commit()
    db.refresh(row)
    assert row.free_used == 0


def test_billing_status_after_login(client, db: Session):
    email = "billing@example.com"
    _seed_auth_code(db, email)
    login = client.post(
        "/api/auth/verify",
        json={"email": email, "code": "123456", "age_confirmed": True},
    ).json()
    token = login["access_token"]
    resp = client.get("/api/agent/billing-status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "free_remaining" in body
    assert "costs" in body
