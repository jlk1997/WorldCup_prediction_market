"""Tests for referral program."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import ReferralBinding, User
from app.db.session import SessionLocal
from app.services.referral_service import ReferralService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_invite_code_generated(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"inviter_{suffix}@test.com", nickname="inviter", fan_coins=0)
    db.add(user)
    db.commit()
    svc = ReferralService(db)
    code = svc.ensure_invite_code(user)
    assert len(code) >= 6
    db.refresh(user)
    assert user.invite_code == code


def test_bind_on_register(db: Session):
    suffix = uuid.uuid4().hex[:8]
    code = f"T{suffix[:7].upper()}"
    inviter = User(email=f"host_{suffix}@test.com", nickname="host", fan_coins=0, invite_code=code)
    db.add(inviter)
    db.commit()
    invitee = User(email=f"guest_{suffix}@test.com", nickname="guest", fan_coins=0)
    db.add(invitee)
    db.commit()
    ReferralService(db).bind_on_register(invitee, code, "127.0.0.1", is_new=True)
    binding = db.query(ReferralBinding).filter(ReferralBinding.invitee_id == invitee.id).first()
    assert binding is not None
    assert binding.inviter_id == inviter.id


def test_weekly_leaderboard(db: Session):
    suffix = uuid.uuid4().hex[:8]
    code = f"L{suffix[:7].upper()}"
    u1 = User(email=f"lb1_{suffix}@test.com", nickname="lb1", fan_coins=0, invite_code=code)
    u2 = User(email=f"lb2_{suffix}@test.com", nickname="lb2", fan_coins=0, profile_completed=True)
    db.add_all([u1, u2])
    db.commit()
    db.add(
        ReferralBinding(
            inviter_id=u1.id,
            invitee_id=u2.id,
            invite_code_used=code,
        )
    )
    db.commit()
    data = ReferralService(db).get_weekly_leaderboard(viewer_id=u1.id)
    ids = {r["user_id"] for r in data["rows"]}
    assert u1.id in ids
    assert data["my_score"] >= 1


def test_referral_api(client, db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"refapi_{suffix}@test.com", nickname="refapi", fan_coins=0)
    db.add(user)
    db.commit()
    from app.services.auth_service import AuthService

    token = AuthService(db)._create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/referral/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["invite_code"]
    assert body["invite_link"]
    assert "effective_invites" in body
    rules = client.get("/api/referral/rules")
    assert rules.status_code == 200
    assert rules.json()["milestones"]
    invites = client.get("/api/referral/invites", headers=headers)
    assert invites.status_code == 200
    assert isinstance(invites.json(), list)
    lb = client.get("/api/referral/leaderboard")
    assert lb.status_code == 200
    assert "rows" in lb.json()
