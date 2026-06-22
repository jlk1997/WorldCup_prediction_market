"""Duel stats and deck preview tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.card_duel_service import CardDuelService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _three_cards(db: Session, user: User) -> list[int]:
    ids = []
    for i in range(3):
        card = CollectibleCard(
            code=f"prev_{uuid.uuid4().hex[:8]}",
            name=f"Card {i}",
            rarity="rare",
            series="test",
            active=True,
            attributes_json={
                "position": ["FWD", "MID", "DEF"][i],
                "overall_rating": 80,
                "combat_stats": {
                    "pace": 75 + i,
                    "shoot": 70,
                    "pass": 72,
                    "dribble": 74,
                    "defend": 65,
                    "physical": 68,
                },
            },
        )
        db.add(card)
        db.flush()
        row = UserCollectibleCard(user_id=user.id, card_id=card.id, star=1, count=1, source="test")
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return ids


def test_deck_preview_summary(db: Session):
    user = User(email=f"st_{uuid.uuid4().hex[:8]}@t.com", nickname="stats")
    db.add(user)
    db.commit()
    ids = _three_cards(db, user)
    preview = CardDuelService(db).deck_preview(user, ids)
    assert preview["count"] == 3
    assert preview["avg_bp"] > 0
    assert len(preview["positions"]) == 3


def test_deck_preview_requires_three(db: Session):
    user = User(email=f"st2_{uuid.uuid4().hex[:8]}@t.com", nickname="s2")
    db.add(user)
    db.commit()
    with pytest.raises(BadRequestError):
        CardDuelService(db).deck_preview(user, [1, 2])


def test_duel_stats_after_ai(db: Session):
    user = User(
        email=f"st3_{uuid.uuid4().hex[:8]}@t.com",
        nickname="s3",
        real_name_verified=True,
    )
    db.add(user)
    db.commit()
    ids = _three_cards(db, user)
    CardDuelService(db).challenge_ai(user, ids, stake_points=0)
    stats = CardDuelService(db).duel_stats(user)
    assert stats["total_duels"] == 1
    assert stats["wins"] + stats["losses"] == 1
    assert "rank_tier" in stats
    assert "duel_elo" in stats
    assert "elo_tier" in stats
