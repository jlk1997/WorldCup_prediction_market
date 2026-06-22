"""卡牌对决安全与并发测试。"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CardDuel, CollectibleCard, User, UserCollectibleCard
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


def _user(db: Session, *, points=1000, verified=True) -> User:
    u = User(
        email=f"sec_{uuid.uuid4().hex[:8]}@test.com",
        nickname=f"n{uuid.uuid4().hex[:4]}",
        redeem_points=points,
        real_name_verified=verified,
        invite_code=f"IV{uuid.uuid4().hex[:4].upper()}",
    )
    db.add(u)
    db.commit()
    return u


def _cards(db: Session, user: User, n: int = 3) -> list[int]:
    ids = []
    for i in range(n):
        card = CollectibleCard(
            code=f"sec_{uuid.uuid4().hex[:8]}",
            name=f"Card {i}",
            rarity="rare",
            series="test",
            active=True,
            attributes_json={"overall_rating": 75 + i},
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
            lock_state="none",
        )
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return ids


def test_pvp_locks_challenger_cards(db: Session):
    ch = _user(db)
    df = _user(db)
    ids = _cards(db, ch)
    svc = CardDuelService(db)
    svc.challenge_user(ch, ids, invite_code=df.invite_code, stake_points=0)
    row = db.get(UserCollectibleCard, ids[0])
    assert row.lock_state == "duel"


def test_cancel_refunds_stake_and_unlocks(db: Session):
    ch = _user(db, points=200)
    df = _user(db)
    ids = _cards(db, ch)
    svc = CardDuelService(db)
    res = svc.challenge_user(ch, ids, invite_code=df.invite_code, stake_points=50)
    ch = db.get(User, ch.id)
    assert ch.redeem_points == 150
    svc.cancel_duel(ch, res["duel_id"])
    ch = db.get(User, ch.id)
    assert ch.redeem_points == 200
    row = db.get(UserCollectibleCard, ids[0])
    assert row.lock_state == "none"


def test_ai_stake_no_inflation(db: Session):
    user = _user(db, points=500)
    ids = _cards(db, user)
    before = user.redeem_points
    stake = 100
    svc = CardDuelService(db)
    for _ in range(3):
        user = db.get(User, user.id)
        svc.challenge_ai(user, ids, stake_points=stake)
    user = db.get(User, user.id)
    assert user.redeem_points <= before + 3 * stake


def test_expire_pending_refunds(db: Session):
    ch = _user(db, points=300)
    df = _user(db)
    ids = _cards(db, ch)
    svc = CardDuelService(db)
    svc.challenge_user(ch, ids, invite_code=df.invite_code, stake_points=40)
    duel = db.query(CardDuel).filter(CardDuel.challenger_id == ch.id).first()
    duel.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=100)
    db.commit()
    result = svc.expire_pending_pvp_duels()
    assert result["expired"] >= 1
    ch = db.get(User, ch.id)
    assert ch.redeem_points == 300
