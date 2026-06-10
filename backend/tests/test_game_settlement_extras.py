"""Settlement isolation, notifications, and admin settle."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.models.commerce import GamePrediction, User, UserNotification
from app.db.session import SessionLocal
from app.services.game_service import GameService
from app.services.notification_service import NotificationService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _utcnow():
    return datetime.utcnow()


def _make_user(db: Session, fan_coins: int = 500) -> User:
    email = f"settle_{uuid.uuid4().hex[:12]}@example.com"
    user = User(email=email, nickname="tester", fan_coins=fan_coins, profile_completed=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_match(db: Session, status: str = "finished", t1_score: int = 2, t2_score: int = 1) -> Match:
    kick = _utcnow() + timedelta(days=1)
    m = Match(
        team1_name="A",
        team2_name="B",
        match_date=kick.strftime("%Y-%m-%d"),
        match_time="18:00",
        status=status,
        home_score=t1_score,
        away_score=t2_score,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _pending(db: Session, user: User, match: Match, pick: str = "home") -> GamePrediction:
    pred = GamePrediction(
        user_id=user.id,
        match_id=match.id,
        pick=pick,
        stake_coins=50,
        status="pending",
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


def test_settle_creates_notification(db: Session):
    user = _make_user(db)
    match = _make_match(db)
    pred = _pending(db, user, match, pick="home")

    GameService(db).settle_finished_matches()

    note = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == user.id, UserNotification.ref_id == pred.id)
        .first()
    )
    assert note is not None
    assert note.category == NotificationService.CATEGORY_PREDICT
    assert "猜对" in note.body or "猜中了" in note.title


def test_void_creates_notification(db: Session):
    user = _make_user(db, fan_coins=200)
    match = _make_match(db, status="postponed", t1_score=0, t2_score=0)
    match.home_score = None
    match.away_score = None
    db.commit()
    pred = _pending(db, user, match)

    GameService(db).void_postponed_predictions()

    note = db.query(UserNotification).filter(UserNotification.ref_id == pred.id).first()
    assert note is not None
    assert "流局" in note.title or "推迟" in note.body


def test_per_row_isolation_one_failure_does_not_block_other(db: Session):
    user1 = _make_user(db)
    user2 = _make_user(db)
    match1 = _make_match(db, t1_score=2, t2_score=0)
    match2 = _make_match(db, t1_score=1, t2_score=0)
    p1 = _pending(db, user1, match1, pick="home")
    p2 = _pending(db, user2, match2, pick="home")

    original = GameService._settle_one
    calls = {"n": 0}

    def flaky_settle(self, user, pred, match):
        calls["n"] += 1
        if pred.id == p1.id:
            raise RuntimeError("simulated arena failure")
        return original(self, user, pred, match)

    with patch.object(GameService, "_settle_one", flaky_settle):
        count = GameService(db).settle_finished_matches()

    db.refresh(p1)
    db.refresh(p2)
    assert count == 1
    assert p1.status == "pending"
    assert p2.status == "won"


def test_notification_service_mark_read(db: Session):
    user = _make_user(db)
    svc = NotificationService(db)
    svc.notify_predict_settled(
        user.id,
        999,
        team1="X",
        team2="Y",
        final_score="1:0",
        status="won",
        points_awarded=30,
    )
    db.commit()
    rows = svc.list_for_user(user.id, unread_only=True)
    assert len(rows) == 1
    updated = svc.mark_read(user.id, [rows[0].id])
    assert updated == 1
    db.commit()
    assert svc.unread_count(user.id) == 0
