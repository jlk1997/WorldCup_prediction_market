"""Tests for game prediction settlement."""

import uuid
from datetime import datetime, timezone

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


def _seed_match_team(db: Session) -> tuple[Match, User]:
    suffix = uuid.uuid4().hex[:8]
    t1_name = f"结算队A_{suffix}"
    t2_name = f"结算队B_{suffix}"
    m = Match(
        group_name="A",
        match_date="2026-06-15",
        match_time="20:00",
        team1_name=t1_name,
        team2_name=t2_name,
        status="finished",
        home_score=2,
        away_score=1,
    )
    user = User(
        email=f"settle_{suffix}@test.com",
        nickname="settle",
        fan_coins=100,
        season_points=0,
        redeem_points=0,
    )
    db.add_all([m, user])
    db.commit()
    db.refresh(m)
    db.refresh(user)
    return m, user


def test_settle_win_awards_dual_points(db: Session):
    match, user = _seed_match_team(db)
    pred = GamePrediction(
        user_id=user.id,
        match_id=match.id,
        pick="home",
        stake_coins=0,
        is_free=True,
        status="pending",
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    gs = GameService(db)
    assert gs._settle_one_transaction(pred.id) is True
    db.refresh(user)
    db.refresh(pred)
    assert pred.status == "won"
    assert user.season_points > 0
    assert user.redeem_points > 0
    assert pred.redeem_points_awarded == int(pred.points_awarded * gs.settings.predict_win_redeem_ratio)


def test_settle_lost_resets_streak(db: Session):
    match, user = _seed_match_team(db)
    user.win_streak = 3
    user.fan_coins = 50
    db.commit()
    pred = GamePrediction(
        user_id=user.id,
        match_id=match.id,
        pick="away",
        stake_coins=50,
        is_free=False,
        status="pending",
    )
    db.add(pred)
    db.commit()
    gs = GameService(db)
    assert gs._settle_one_transaction(pred.id) is True
    db.refresh(user)
    db.refresh(pred)
    assert pred.status == "lost"
    assert user.win_streak == 0
    assert user.fan_coins == 50


def test_void_postponed_refunds_stake(db: Session):
    suffix = uuid.uuid4().hex[:8]
    m = Match(
        team1_name=f"延期A_{suffix}",
        team2_name=f"延期B_{suffix}",
        status="postponed",
        match_date="2026-07-01",
        match_time="12:00",
    )
    user = User(email=f"void_{suffix}@test.com", nickname="void", fan_coins=50)
    db.add_all([m, user])
    db.flush()
    pred = GamePrediction(
        user_id=user.id,
        match_id=m.id,
        pick="home",
        stake_coins=30,
        is_free=False,
        status="pending",
    )
    db.add(pred)
    db.commit()
    assert GameService(db)._void_one_transaction(pred.id) is True
    db.refresh(pred)
    db.refresh(user)
    assert pred.status == "void"
    assert user.fan_coins == 80
