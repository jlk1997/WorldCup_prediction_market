"""Unit tests for arena battalion service."""

from datetime import date

import pytest

from app.db.models import Match
from app.db.models.commerce import User
from app.db.session import SessionLocal
from app.services.arena_service import ArenaService, _date_ref, _player_date_ref


def test_date_ref_encoding():
    d = date(2026, 6, 8)
    assert _date_ref(d) == 20260608


def test_player_date_ref_encoding():
    d = date(2026, 6, 8)
    ref = _player_date_ref(42, d)
    assert ref == 42 * 100000 + 20260608


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_record_activity_idempotent(db):
    user = db.query(User).filter(User.status == "active").first()
    if not user:
        pytest.skip("No active user in database")
    svc = ArenaService(db)
    today = date.today()
    ref_id = _date_ref(today) + 99999  # unlikely collision
    first = svc.record_activity(
        user,
        "signin_test",
        team_id=user.favorite_team_id,
        battalion_delta=1,
        ref_type="date",
        ref_id=ref_id,
    )
    second = svc.record_activity(
        user,
        "signin_test",
        team_id=user.favorite_team_id,
        battalion_delta=1,
        ref_type="date",
        ref_id=ref_id,
    )
    db.rollback()
    assert first is True
    assert second is False


def test_recalc_arena_tiers(db):
    svc = ArenaService(db)
    updated = svc.recalc_arena_tiers()
    db.rollback()
    assert updated >= 0


def test_team_rank_endpoint(client):
    resp = client.get("/api/arena/team-rank")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_match_arena_endpoint(client):
    db = SessionLocal()
    try:
        match = db.query(Match).first()
        if not match:
            pytest.skip("No matches")
        resp = client.get(f"/api/arena/match/{match.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["match_id"] == match.id
        assert "home" in body and "away" in body
    finally:
        db.close()


def test_process_matchday_rewards(db):
    svc = ArenaService(db)
    count = svc.process_matchday_goal_rewards()
    db.rollback()
    assert count >= 0
