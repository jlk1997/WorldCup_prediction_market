"""Tests for fan profile, cheer, and quiz APIs."""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import Match, PlayerDetailed, Team
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


def _login(client, db: Session, email: str):
    _seed_auth_code(db, email)
    resp = client.post("/api/auth/verify", json={"email": email, "code": "123456", "age_confirmed": True})
    assert resp.status_code == 200
    return resp.json()


def _first_team_with_players(db: Session) -> tuple[int, list[int]]:
    team = db.query(Team).order_by(Team.id).first()
    if not team:
        pytest.skip("no teams in database")
    players = (
        db.query(PlayerDetailed)
        .filter(PlayerDetailed.team_id == team.id)
        .limit(3)
        .all()
    )
    if not players:
        pytest.skip("no players for team")
    return team.id, [p.id for p in players]


def _scheduled_match(db: Session) -> Match | None:
    return (
        db.query(Match)
        .filter((Match.status == "scheduled") | (Match.status.is_(None)))
        .order_by(Match.match_date)
        .first()
    )


def test_profile_same_team_rejected(client, db: Session):
    login = _login(client, db, "fan_same_team@example.com")
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    team_id, player_ids = _first_team_with_players(db)
    resp = client.put(
        "/api/profile/setup",
        json={
            "main_team_id": team_id,
            "secondary_team_id": team_id,
            "player_ids": player_ids[:1],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_profile_setup_rejects_four_players(client, db: Session):
    login = _login(client, db, "fan_four_players@example.com")
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    team_id, _ = _first_team_with_players(db)
    resp = client.put(
        "/api/profile/setup",
        json={"main_team_id": team_id, "player_ids": [1, 2, 3, 4]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_profile_setup_and_status(client, db: Session):
    login = _login(client, db, "fan_setup@example.com")
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    team_id, player_ids = _first_team_with_players(db)

    setup = client.put(
        "/api/profile/setup",
        json={"main_team_id": team_id, "player_ids": player_ids[:1]},
        headers=headers,
    )
    assert setup.status_code == 200
    body = setup.json()
    assert body["profile_completed"] is True
    assert body["main_team"]["id"] == team_id

    status = client.get("/api/profile/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["profile_completed"] is True


def test_cheer_requires_profile(client, db: Session):
    login = _login(client, db, "fan_cheer_no_profile@example.com")
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    match = _scheduled_match(db)
    if not match:
        pytest.skip("no scheduled match")
    team = db.query(Team).filter(Team.name == match.team1_name).first()
    if not team:
        pytest.skip("team not linked")
    resp = client.post(
        "/api/game/cheer",
        json={"match_id": match.id, "team_id": team.id},
        headers=headers,
    )
    assert resp.status_code == 400


def test_cheer_idempotent(client, db: Session):
    login = _login(client, db, "fan_cheer_idem@example.com")
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    team_id, player_ids = _first_team_with_players(db)
    client.put(
        "/api/profile/setup",
        json={"main_team_id": team_id, "player_ids": player_ids[:1]},
        headers=headers,
    )
    user = db.get(User, login["user"]["id"])
    db.refresh(user)
    if user.fan_coins < 5:
        user.fan_coins = 100
        db.commit()

    match = _scheduled_match(db)
    if not match:
        pytest.skip("no scheduled match")
    team = db.get(Team, team_id)
    if not team or team.name not in {match.team1_name, match.team2_name}:
        pytest.skip("main team not in match")

    first = client.post(
        "/api/game/cheer",
        json={"match_id": match.id, "team_id": team_id},
        headers=headers,
    )
    if first.status_code != 200:
        pytest.skip(f"cheer window closed or unavailable: {first.text}")

    second = client.post(
        "/api/game/cheer",
        json={"match_id": match.id, "team_id": team_id},
        headers=headers,
    )
    assert second.status_code == 400


def test_quiz_once_per_day(client, db: Session):
    import uuid

    email = f"fan_quiz_{uuid.uuid4().hex[:8]}@example.com"
    login = _login(client, db, email)
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    today = client.get("/api/game/quiz/today", headers=headers)
    assert today.status_code == 200
    q = today.json()
    assert "question" in q
    assert "options" in q

    ans = client.post("/api/game/quiz/answer", json={"answer_index": 0}, headers=headers)
    assert ans.status_code == 200

    again = client.post("/api/game/quiz/answer", json={"answer_index": 0}, headers=headers)
    assert again.status_code == 400
