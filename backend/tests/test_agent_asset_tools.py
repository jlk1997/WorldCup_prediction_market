"""Agent asset tools tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.agents.asset_tools import AgentAssetTools
from app.agents.tool_registry import ToolRouter
from app.agents.tools import AgentTools
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user_with_cards(db: Session) -> User:
    user = User(
        email=f"agent_{uuid.uuid4().hex[:8]}@test.com",
        nickname="agent_fan",
        duel_elo=1050,
    )
    db.add(user)
    db.commit()
    for i in range(3):
        card = CollectibleCard(
            code=f"ag_{uuid.uuid4().hex[:6]}",
            name=f"Agent Card {i}",
            rarity="rare",
            series="test",
            active=True,
            attributes_json={
                "position": ["FWD", "MID", "DEF"][i],
                "overall_rating": 80,
                "combat_stats": {
                    "pace": 75,
                    "shoot": 74,
                    "pass": 73,
                    "dribble": 72,
                    "defend": 71,
                    "physical": 70,
                },
            },
        )
        db.add(card)
        db.flush()
        db.add(
            UserCollectibleCard(
                user_id=user.id,
                card_id=card.id,
                star=1,
                count=1,
                source="test",
            )
        )
    db.commit()
    return user


def test_agent_asset_tools_recommend(db: Session):
    user = _user_with_cards(db)
    rec = AgentAssetTools(db, user.id).recommend_duel_deck()
    assert "error" not in rec
    assert len(rec["card_ids"]) == 3
    assert rec.get("reason")


def test_tool_router_requires_login_for_asset_tools(db: Session):
    router = ToolRouter(AgentTools(db))
    router.user_id = None
    out = router.dispatch("recommend_duel_deck", {})
    assert "error" in out


def test_get_user_market_hints(db: Session):
    user = _user_with_cards(db)
    hints = AgentAssetTools(db, user.id).get_user_market_hints(limit=3)
    assert "error" not in hints
    assert "disclaimer" in hints
