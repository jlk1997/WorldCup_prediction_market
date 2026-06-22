"""卡牌军团加成测试。"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models import Team
from app.db.models.commerce import CardStake, CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.card_battalion_service import CardBattalionService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _team_id(db: Session) -> int:
    """Use existing team or a synthetic id for boost math (no Team row required)."""
    row = db.query(Team.id).first()
    if row:
        return row[0]
    return 900000 + int(uuid.uuid4().hex[:4], 16) % 10000


def test_crest_boost_capped(db: Session):
    user = User(email=f"bb_{uuid.uuid4().hex[:8]}@test.com", nickname="bb")
    team_id = _team_id(db)
    user.favorite_team_id = team_id
    db.add(user)
    db.flush()
    for i in range(5):
        card = CollectibleCard(
            code=f"crest_{uuid.uuid4().hex[:6]}",
            name=f"Crest {i}",
            rarity="rare",
            series="team_crest",
            team_id=team_id,
            active=True,
        )
        db.add(card)
        db.flush()
        db.add(UserCollectibleCard(user_id=user.id, card_id=card.id, star=1, count=1, source="test"))
    db.commit()
    pct = CardBattalionService(db).compute_battalion_card_boost(user, team_id)
    assert pct == pytest.approx(0.09)


def test_staked_player_boost(db: Session):
    user = User(email=f"bb2_{uuid.uuid4().hex[:8]}@test.com", nickname="bb2")
    team_id = _team_id(db)
    db.add(user)
    db.flush()
    card = CollectibleCard(
        code=f"squad_{uuid.uuid4().hex[:6]}",
        name="Player",
        rarity="rare",
        series="team_squad",
        team_id=team_id,
        active=True,
    )
    db.add(card)
    db.flush()
    row = UserCollectibleCard(user_id=user.id, card_id=card.id, star=1, count=1, source="test")
    db.add(row)
    db.flush()
    db.add(
        CardStake(
            user_id=user.id,
            user_card_id=row.id,
            card_id=card.id,
            rarity="rare",
            status="active",
        )
    )
    db.commit()
    pct = CardBattalionService(db).compute_battalion_card_boost(user, team_id)
    assert pct == pytest.approx(0.05)


def test_summary_for_user(db: Session):
    user = User(email=f"bb3_{uuid.uuid4().hex[:8]}@test.com", nickname="bb3")
    team = db.query(Team).first()
    if not team:
        pytest.skip("no teams in database")
    db.add(user)
    db.flush()
    card = CollectibleCard(
        code=f"crest2_{uuid.uuid4().hex[:6]}",
        name="Crest",
        rarity="common",
        series="team_crest",
        team_id=team.id,
        active=True,
    )
    db.add(card)
    db.flush()
    db.add(UserCollectibleCard(user_id=user.id, card_id=card.id, star=1, count=1, source="test"))
    db.commit()
    rows = CardBattalionService(db).summary_for_user(user)
    assert len(rows) == 1
    assert rows[0]["team_id"] == team.id
    assert rows[0]["boost_pct"] == 3.0
