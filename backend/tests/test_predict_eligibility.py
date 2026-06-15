"""Tests for prediction eligibility rules."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.predict_eligibility import is_match_predictable, match_has_live_signals
from app.db.models import Match
from app.db.models.commerce import User
from app.db.session import SessionLocal
from app.core.exceptions import BadRequestError
from app.services.game_service import GameService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_match_has_live_signals():
    m = Match(status="scheduled", home_score=1, away_score=0)
    assert match_has_live_signals(m) is True
    m2 = Match(status="scheduled", minute=45)
    assert match_has_live_signals(m2) is True
    m3 = Match(status="scheduled")
    assert match_has_live_signals(m3) is False


def test_is_match_predictable_future():
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    m = Match(
        status="scheduled",
        match_date=future.strftime("%Y-%m-%d"),
        match_time="18:00",
    )
    assert is_match_predictable(m, close_minutes_before=30) is True


def test_is_match_predictable_past_kickoff():
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    m = Match(
        status="scheduled",
        match_date=past.strftime("%Y-%m-%d"),
        match_time=past.strftime("%H:%M"),
    )
    assert is_match_predictable(m, close_minutes_before=30) is False


def test_submit_rejects_finished_match(db: Session):
    suffix = uuid.uuid4().hex[:8]
    m = Match(
        group_name="A",
        match_date="2026-07-01",
        match_time="18:00",
        team1_name=f"A_{suffix}",
        team2_name=f"B_{suffix}",
        status="finished",
        home_score=1,
        away_score=0,
    )
    user = User(email=f"elig_{suffix}@test.com", nickname="e", fan_coins=100)
    db.add_all([m, user])
    db.commit()
    db.refresh(m)
    db.refresh(user)
    gs = GameService(db)
    with pytest.raises(BadRequestError):
        gs.submit_prediction(user, m.id, "home", 0, use_free=True)
