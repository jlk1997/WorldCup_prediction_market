"""QQ group join reward (honor claim, one-time per user)."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CoinLedger, User
from app.db.session import SessionLocal
from app.services.game_service import GameService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user(db: Session) -> User:
    u = User(
        email=f"qq_{uuid.uuid4().hex[:10]}@example.com",
        nickname="qq_tester",
        fan_coins=100,
        profile_completed=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_qq_group_claim_once(db: Session):
    user = _user(db)
    svc = GameService(db)
    first = svc.claim_qq_group_reward(user)
    db.commit()
    assert first["already_claimed"] is False
    assert first["coins_added"] == 50
    assert user.fan_coins == 150

    second = svc.claim_qq_group_reward(user)
    assert second["already_claimed"] is True
    assert second["coins_added"] == 0

    rows = (
        db.query(CoinLedger)
        .filter(CoinLedger.user_id == user.id, CoinLedger.reason == "qq_group_join")
        .all()
    )
    assert len(rows) == 1


def test_daily_status_includes_qq_task(db: Session):
    user = _user(db)
    svc = GameService(db)
    status = svc.get_daily_status(user)
    keys = [c["key"] for c in status["checklist"]]
    assert "qq_group" in keys
    assert status["qq_group_claimed"] is False

    svc.claim_qq_group_reward(user)
    db.commit()
    status2 = svc.get_daily_status(user)
    assert status2["qq_group_claimed"] is True
    assert "qq_group" not in [c["key"] for c in status2["checklist"]]
