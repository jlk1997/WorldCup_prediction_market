"""Duel ELO and recommend deck tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.db.models.commerce import CardDuel, CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.card_duel_service import CardDuelService
from app.services.duel_elo_service import apply_pvp_elo, recommend_deck_from_cards
from app.services.combat_engine import build_combat_card_from_virtual


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _cards(db: Session, user: User, n: int = 3) -> list[int]:
    ids = []
    positions = ["FWD", "MID", "DEF"]
    for i in range(n):
        card = CollectibleCard(
            code=f"elo_{uuid.uuid4().hex[:8]}",
            name=f"Elo Card {i}",
            rarity="rare",
            series="test",
            active=True,
            attributes_json={
                "position": positions[i % 3],
                "overall_rating": 82 + i,
                "combat_stats": {
                    "pace": 78,
                    "shoot": 76,
                    "pass": 74,
                    "dribble": 72,
                    "defend": 70,
                    "physical": 68,
                },
            },
        )
        db.add(card)
        db.flush()
        row = UserCollectibleCard(
            user_id=user.id,
            card_id=card.id,
            star=1,
            count=1,
            source="test",
            tradable=True,
        )
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return ids


def test_apply_pvp_elo_symmetric():
    deltas = apply_pvp_elo(1000, 1000, winner_id=1, challenger_id=1, defender_id=2)
    assert deltas["challenger_delta"] > 0
    assert deltas["defender_delta"] < 0
    assert deltas["challenger_delta"] + abs(deltas["defender_delta"]) > 0


def test_ai_duel_updates_elo(db: Session):
    user = User(
        email=f"elo_{uuid.uuid4().hex[:8]}@test.com",
        nickname="elo",
        real_name_verified=True,
        duel_elo=1000,
    )
    db.add(user)
    db.commit()
    ids = _cards(db, user)
    before = user.duel_elo
    res = CardDuelService(db).challenge_ai(user, ids, stake_points=0)
    db.refresh(user)
    duel = db.get(CardDuel, res["duel_id"])
    assert duel is not None
    assert duel.challenger_elo_delta != 0 or res["won"] is False
    assert user.duel_elo != before or res["won"] is False
    assert "elo_delta" in res
    assert "duel_elo" in res


def test_recommend_deck_from_service(db: Session):
    user = User(email=f"rec_{uuid.uuid4().hex[:8]}@test.com", nickname="rec")
    db.add(user)
    db.commit()
    _cards(db, user, 5)
    rec = CardDuelService(db).recommend_deck(user)
    assert len(rec["card_ids"]) == 3
    assert rec["avg_bp"] > 0
    assert rec.get("reason")


def test_recommend_deck_insufficient_cards(db: Session):
    user = User(email=f"rec2_{uuid.uuid4().hex[:8]}@test.com", nickname="rec2")
    db.add(user)
    db.commit()
    _cards(db, user, 2)
    with pytest.raises(BadRequestError, match="不足"):
        CardDuelService(db).recommend_deck(user)


def test_elo_leaderboard_only_participants(db: Session):
    idle = User(
        email=f"idle_{uuid.uuid4().hex[:8]}@test.com",
        nickname="idle",
        duel_elo=1500,
    )
    active = User(
        email=f"act_{uuid.uuid4().hex[:8]}@test.com",
        nickname="active",
        duel_elo=1100,
        real_name_verified=True,
    )
    db.add_all([idle, active])
    db.commit()
    ids = _cards(db, active)
    CardDuelService(db).challenge_ai(active, ids, stake_points=0)
    board = CardDuelService(db).duel_leaderboard(limit=20, by="elo")
    board_ids = {r["user_id"] for r in board}
    assert active.id in board_ids
    assert idle.id not in board_ids


def test_recommend_deck_from_cards_combinatorics():
    cards = [
        build_combat_card_from_virtual(
            {
                "name": f"C{i}",
                "rarity": "rare",
                "user_card_id": i + 1,
                "position": ["FWD", "MID", "DEF"][i % 3],
                "combat_stats": {
                    "pace": 70 + i * 5,
                    "shoot": 70,
                    "pass": 70,
                    "dribble": 70,
                    "defend": 70,
                    "physical": 70,
                },
            }
        )
        for i in range(4)
    ]
    rec = recommend_deck_from_cards(cards)
    assert len(rec["card_ids"]) == 3
