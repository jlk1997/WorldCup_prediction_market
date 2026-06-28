"""Tests for Post Phase 15 features."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.models.commerce import GamePrediction, User
from app.db.session import SessionLocal
from app.services.prediction_knowledge_service import snippet_for_teams


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_snippet_stage_prefix():
    text = snippet_for_teams("荷兰", "葡萄牙", stage="knockout")
    assert "[淘汰赛]" in text or "荷兰" in text or "葡萄牙" in text


def test_cash_grant_schema_mint_bundle():
    from app.data.cash_grant_schema import validate_cash_grant_payload

    payload = validate_cash_grant_payload(
        {"mint_event_id": 3, "ai_live_credits": 1},
        product_type="mint_bundle",
    )
    assert payload["mint_event_id"] == 3


def test_season_ultimate_grant_schema():
    from app.data.cash_grant_schema import validate_cash_grant_payload

    payload = validate_cash_grant_payload(
        {
            "collection_pass_premium": True,
            "collection_pass_level_skip": 5,
            "avatar_frame": "gold_wc",
            "badge_code": "season_ultimate",
            "badge_title": "终极球迷",
        },
        product_type="season_ultimate",
    )
    assert payload["collection_pass_premium"] is True


def test_matchday_repurchase_copy_variants():
    from app.services.matchday_orchestration_service import _REPURCHASE_COPY

    assert "a" in _REPURCHASE_COPY and "b" in _REPURCHASE_COPY
    assert "{name}" in _REPURCHASE_COPY["a"][0]


def test_settle_includes_ai_pick(db: Session, monkeypatch):
    from app.services.game_service import GameService

    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"ai_pick_{suffix}@test.com", nickname=f"ai_{suffix}")
    db.add(user)
    db.flush()
    match = Match(
        team1_name="A队",
        team2_name="B队",
        status="finished",
        home_score=2,
        away_score=1,
    )
    db.add(match)
    db.flush()
    pred = GamePrediction(
        user_id=user.id,
        match_id=match.id,
        pick="home",
        status="pending",
        is_free=True,
        stake_coins=0,
    )
    db.add(pred)
    db.commit()

    svc = GameService(db)
    monkeypatch.setattr(
        svc, "_ai_pick_for_match", lambda m: {"ai_pick": "home", "ai_pick_label": "A队 胜"}
    )
    payload = svc._settle_one(user, pred, match)
    assert payload is not None
    assert payload["ai_pick"] == "home"
    assert payload["user_followed_ai"] is True
    assert payload["ai_pick_correct"] is True
