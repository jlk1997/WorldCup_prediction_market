"""Tests for immersion / referral fixes."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import AuthCode, User
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


def test_referral_preview_invalid(client):
    resp = client.get("/api/referral/preview", params={"code": "BADCODE1"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


def test_referral_preview_and_login_fields(client, db: Session):
    inviter_email = "inviter_preview@example.com"
    token = _login(client, db, inviter_email)
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    inviter = db.query(User).filter(User.email == inviter_email).first()
    inviter.invite_code = "TESTREF1"
    db.commit()

    preview = client.get("/api/referral/preview", params={"code": "TESTREF1"}).json()
    assert preview["valid"] is True
    assert preview["inviter_nickname"] == me["nickname"]

    invitee_email = "invitee_preview@example.com"
    _seed_auth_code(db, invitee_email)
    reg = client.post(
        "/api/auth/verify",
        json={
            "email": invitee_email,
            "code": "123456",
            "age_confirmed": True,
            "invite_code": "TESTREF1",
        },
    )
    assert reg.status_code == 200
    body = reg.json()
    assert body["referral"]["bound"] is True
    assert body["referral"]["inviter_nickname"] == me["nickname"]


def test_daily_status_and_signin_streak(client, db: Session):
    email = f"daily_{uuid.uuid4().hex[:8]}@example.com"
    token = _login(client, db, email)
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get("/api/game/daily-status", headers=headers).json()
    assert status["signed_today"] is False
    assert "free_predict" in status
    assert status["free_predict"]["limit"] >= 1

    signin = client.post("/api/game/signin", headers=headers).json()
    assert signin["added"] >= 20
    assert signin["signin_streak"] == 1

    status2 = client.get("/api/game/daily-status", headers=headers).json()
    assert status2["signed_today"] is True
    assert status2["signin_streak"] == 1
    assert status2["next_action"]["key"] in ("quiz", "predict", "done", "pending", "arena")
    assert "checklist" in status2
    assert status2["ritual_progress"]["total"] >= 3

    me = client.get("/api/auth/me", headers=headers).json()
    assert me.get("signin_streak") == 1
    assert me.get("last_signin_date") is not None


def test_predict_preview(client, db: Session):
    email = "predict_preview@example.com"
    token = _login(client, db, email)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        "/api/game/predict/preview",
        headers=headers,
        params={"pick": "home", "stake_coins": 50, "use_free": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["on_win"]["season_points"] >= 30
    assert data["on_win"]["coins_returned"] == 100


def test_matches_embed_pick_stats(client, db: Session):
    email = f"pick_stats_{uuid.uuid4().hex[:8]}@example.com"
    token = _login(client, db, email)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/game/matches", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    if rows and not rows[0].get("user_predicted"):
        assert "pick_stats" in rows[0]
