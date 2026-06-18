"""Tests for daily-status activation segment and next_action priority."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.db.models import Match, Team
from app.db.models.commerce import GamePrediction, User
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


def _future_match(db: Session, suffix: str) -> Match:
    kick = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)
    m = Match(
        group_name="A",
        match_date=kick.strftime("%Y-%m-%d"),
        match_time=kick.strftime("%H:%M"),
        team1_name=f"激活队A_{suffix}",
        team2_name=f"激活队B_{suffix}",
        status="scheduled",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _user(db: Session, suffix: str, **kwargs) -> User:
    u = User(
        email=f"act_{suffix}@test.com",
        nickname=f"act_{suffix}",
        fan_coins=100,
        **kwargs,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_activation_segment_never_predicted(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = _user(db, suffix)
    gs = GameService(db)
    status = gs.get_daily_status(user)
    assert status["activation_segment"] == "never_predicted"
    assert status["predict_count_total"] == 0
    assert status["next_predictable_match"] is not None
    assert status["activation_nudge"]["cta_label"] == "去猜第一场"


def test_activation_segment_profile_only(db: Session):
    suffix = uuid.uuid4().hex[:8]
    _future_match(db, suffix)
    today = datetime.now(timezone.utc).date()
    user = _user(db, suffix, profile_completed=True, favorite_team_id=None, last_signin_date=today)
    gs = GameService(db)
    with patch.object(gs, "qq_group_claimed", return_value=True):
        status = gs.get_daily_status(user)
    assert status["activation_segment"] == "profile_only"
    assert status["activation_nudge"]["title"] == "档案已就绪"
    assert status["next_action"]["key"] == "first_predict"


def test_activation_segment_one_and_done(db: Session):
    suffix = uuid.uuid4().hex[:8]
    m1 = _future_match(db, suffix)
    m2 = _future_match(db, suffix + "b")
    user = _user(db, suffix, profile_completed=True, last_signin_date=datetime.now(timezone.utc).date())
    db.add(
        GamePrediction(
            user_id=user.id,
            match_id=m1.id,
            pick="home",
            stake_coins=0,
            is_free=True,
            status="pending",
        )
    )
    db.commit()
    gs = GameService(db)
    with patch.object(gs, "qq_group_claimed", return_value=True):
        status = gs.get_daily_status(user)
    assert status["activation_segment"] == "one_and_done"
    assert status["predict_count_total"] == 1
    assert status["next_action"]["key"] == "second_predict"
    assert str(m2.id) in (status["next_action"].get("path") or "")
    assert status["activation_nudge"] is not None
    assert "再猜" in status["activation_nudge"]["title"] or "再来" in status["activation_nudge"]["title"]


def test_activation_nudge_fallback_without_next_match(db: Session):
    suffix = uuid.uuid4().hex[:8]
    m1 = _future_match(db, suffix)
    user = _user(db, suffix, profile_completed=True, last_signin_date=datetime.now(timezone.utc).date())
    db.add(
        GamePrediction(
            user_id=user.id,
            match_id=m1.id,
            pick="home",
            stake_coins=0,
            is_free=True,
            status="pending",
        )
    )
    db.commit()
    gs = GameService(db)
    with patch.object(gs, "qq_group_claimed", return_value=True), patch.object(
        gs, "_next_predictable_match_for_user", return_value=None
    ):
        status = gs.get_daily_status(user)
    assert status["activation_segment"] == "one_and_done"
    assert status["activation_nudge"] is not None
    assert status["activation_nudge"]["path"] == "/predict"
    assert status["next_action"]["key"] == "second_predict"
    assert status["next_action"]["path"] == "/predict"


def test_activation_segment_active(db: Session):
    suffix = uuid.uuid4().hex[:8]
    m1 = _future_match(db, suffix)
    m2 = _future_match(db, suffix + "b")
    user = _user(db, suffix, profile_completed=True, last_signin_date=datetime.now(timezone.utc).date())
    db.add_all(
        [
            GamePrediction(
                user_id=user.id,
                match_id=m1.id,
                pick="home",
                stake_coins=0,
                is_free=True,
                status="pending",
            ),
            GamePrediction(
                user_id=user.id,
                match_id=m2.id,
                pick="draw",
                stake_coins=0,
                is_free=True,
                status="pending",
            ),
        ]
    )
    db.commit()
    gs = GameService(db)
    status = gs.get_daily_status(user)
    assert status["activation_segment"] == "active"
    assert status["predict_count_total"] == 2
    assert status.get("activation_nudge") is None
