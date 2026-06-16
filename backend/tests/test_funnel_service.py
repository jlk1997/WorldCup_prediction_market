"""Tests for growth funnel summary."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import GamePrediction, User
from app.db.session import SessionLocal
from app.services.funnel_service import FunnelService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_funnel_summary_counts(db: Session):
    suffix = uuid.uuid4().hex[:8]
    u1 = User(
        email=f"funnel_{suffix}@test.com",
        nickname="漏斗测试",
        fan_coins=0,
        profile_completed=True,
        created_at=_utcnow() - timedelta(days=1),
    )
    u2 = User(
        email=f"funnel2_{suffix}@test.com",
        nickname="漏斗测试2",
        fan_coins=0,
        profile_completed=False,
        created_at=_utcnow() - timedelta(days=1),
    )
    db.add_all([u1, u2])
    db.flush()
    db.add(GamePrediction(user_id=u1.id, match_id=1, pick="home", status="pending"))
    db.commit()

    summary = FunnelService(db).summary(days=7)
    assert summary["registered"] >= 2
    assert summary["profile_completed"] >= 1
    assert summary["first_predict_users"] >= 1
