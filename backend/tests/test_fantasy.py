"""Fantasy 数字阵容 — 计分与周榜结算测试。"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.db.models import Match
from app.db.models.commerce import CollectibleCard, FantasyLineup, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.fantasy_service import FantasyService, current_period_key, previous_period_key


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _player_card(db: Session, user: User, *, name: str = "Fantasy Striker") -> tuple[UserCollectibleCard, CollectibleCard]:
    suffix = uuid.uuid4().hex[:6]
    card = CollectibleCard(
        code=f"fantasy_player_{suffix}",
        name=name,
        rarity="rare",
        series="test",
        active=True,
        player_id=None,
        attributes_json={"overall_rating": 85, "position": "ST"},
    )
    db.add(card)
    db.flush()
    row = UserCollectibleCard(
        user_id=user.id,
        card_id=card.id,
        star=2,
        count=1,
        source="test",
        tradable=True,
        serial_no=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    db.refresh(card)
    return row, card


def test_save_lineup_validates_cards(db: Session):
    user = User(email=f"fantasy_{uuid.uuid4().hex[:8]}@test.com", nickname="fantasy")
    db.add(user)
    db.commit()
    svc = FantasyService(db)
    with pytest.raises(BadRequestError):
        svc.save_lineup(user, [999999])


def test_score_match_idempotent(db: Session):
    user = User(email=f"fantasy_{uuid.uuid4().hex[:8]}@test.com", nickname="fantasy")
    db.add(user)
    db.commit()
    row, card = _player_card(db, user, name="Goal Scorer")
    period = current_period_key()
    db.add(FantasyLineup(user_id=user.id, period_key=period, slots_json=[row.id], score=0))
    db.commit()

    match = Match(
        team1_name="Team A",
        team2_name="Team B",
        status="finished",
        events_json=[{"type": "goal", "player": card.name}],
        live_updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(match)
    db.commit()

    svc = FantasyService(db)
    n1 = svc.score_match(match)
    n2 = svc.score_match(match)
    assert n1 >= 1
    assert n2 == 0

    lineup = db.query(FantasyLineup).filter(FantasyLineup.user_id == user.id).first()
    assert lineup.score > 0


def test_settle_previous_week_idempotent(db: Session):
    user = User(email=f"fantasy_{uuid.uuid4().hex[:8]}@test.com", nickname="fantasy", fan_coins=0)
    db.add(user)
    db.commit()
    period = previous_period_key()
    lineup = FantasyLineup(user_id=user.id, period_key=period, slots_json=[1], score=100)
    db.add(lineup)
    db.commit()

    svc = FantasyService(db)
    r1 = svc.settle_previous_week()
    r2 = svc.settle_previous_week()
    assert r1["awarded"] >= 1
    assert r2["awarded"] == 0
    user = db.get(User, user.id)
    assert (user.fan_coins or 0) > 0


def test_user_rank_zero_score(db: Session):
    user = User(email=f"fantasy_{uuid.uuid4().hex[:8]}@test.com", nickname="fantasy")
    db.add(user)
    db.commit()
    rank = FantasyService(db).user_rank(user)
    assert rank["on_board"] is False
    assert rank["rank"] is None
