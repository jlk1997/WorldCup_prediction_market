"""Unit tests for arena battalion service."""

from datetime import date

import pytest

from app.db.models import Match
from app.db.models.commerce import User
from app.db.session import SessionLocal
from app.services.arena_service import (
    ArenaService,
    PREDICT_CHEER_COMBO_BATTALION,
    UNDERDOG_BATTALION_BONUS,
    _date_ref,
    _player_date_ref,
    _team_date_ref,
    cheer_affiliation,
    cheer_rewards_for_affiliation,
)


def test_date_ref_encoding():
    d = date(2026, 6, 8)
    assert _date_ref(d) == 20260608


def test_player_date_ref_encoding():
    d = date(2026, 6, 8)
    ref = _player_date_ref(42, d)
    assert ref == 42 * 100000 + 20260608


def test_team_date_ref_encoding():
    d = date(2026, 6, 8)
    ref = _team_date_ref(7, d)
    assert ref == 7 * 100000000 + 20260608


def test_cheer_affiliation_and_rewards():
    class U:
        favorite_team_id = 1
        secondary_team_id = 2

    user = U()
    assert cheer_affiliation(user, 1) == "primary"
    assert cheer_affiliation(user, 2) == "secondary"
    assert cheer_affiliation(user, 99) == "neutral"
    assert cheer_rewards_for_affiliation("primary") == (10, 10)
    assert cheer_rewards_for_affiliation("secondary") == (10, 10)
    assert cheer_rewards_for_affiliation("neutral") == (5, 5)


def test_today_matches_endpoint(client):
    resp = client.get("/api/arena/today-matches")
    assert resp.status_code == 401


def test_spot_cheer_endpoint_requires_auth(client):
    resp = client.get("/api/arena/spot-cheer")
    assert resp.status_code == 401


def test_arena_post_endpoints_require_auth(client):
    for method, path, body in [
        ("post", "/api/arena/spot-cheer", {"team_id": 1, "slogan_index": 0}),
        ("post", "/api/arena/boost/star", {"player_id": 1}),
        ("post", "/api/arena/boost/cheer-extra", {"match_id": 1}),
        ("post", "/api/arena/boost/matchday-rally", {}),
        ("post", "/api/game/cheer", {"match_id": 1, "team_id": 1}),
    ]:
        resp = getattr(client, method)(path, json=body)
        assert resp.status_code == 401, path


def test_record_activity_handles_integrity_error(db):
    user = db.query(User).filter(User.status == "active").first()
    if not user:
        pytest.skip("No active user in database")
    svc = ArenaService(db)
    today = date.today()
    ref_id = _date_ref(today) + 88888
    with db.begin_nested():
        assert svc.record_activity(
            user,
            "integrity_test",
            team_id=user.favorite_team_id,
            battalion_delta=1,
            ref_type="date",
            ref_id=ref_id,
        )
    dup = svc.record_activity(
        user,
        "integrity_test",
        team_id=user.favorite_team_id,
        battalion_delta=1,
        ref_type="date",
        ref_id=ref_id,
    )
    db.rollback()
    assert dup is False


def test_spot_slot_ref_encoding():
    d = date(2026, 6, 8)
    from app.services.arena_service import _spot_slot_ref

    assert _spot_slot_ref(d, 0) == 2026060800
    assert _spot_slot_ref(d, 2) == 2026060802


def test_underdog_bonus_logic():
    assert cheer_rewards_for_affiliation("neutral") == (5, 5)
    assert PREDICT_CHEER_COMBO_BATTALION == 5
    assert UNDERDOG_BATTALION_BONUS == 3


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
