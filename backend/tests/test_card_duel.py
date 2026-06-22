"""卡牌对决测试。"""

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


def _cards(db: Session, user: User, n: int = 3) -> list[int]:
    ids = []
    for i in range(n):
        card = CollectibleCard(
            code=f"duel_{uuid.uuid4().hex[:8]}",
            name=f"Duel Card {i}",
            rarity="rare",
            series="test",
            active=True,
            attributes_json={"overall_rating": 80 + i},
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
            serial_no=i + 1,
        )
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return ids


def test_ai_duel_settles(db: Session):
    user = User(
        email=f"duel_{uuid.uuid4().hex[:8]}@test.com",
        nickname="duel",
        redeem_points=500,
        real_name_verified=True,
    )
    db.add(user)
    db.commit()
    ids = _cards(db, user)
    res = CardDuelService(db).challenge_ai(user, ids, stake_points=0)
    assert res["ok"] is True
    assert "duel_id" in res


def test_stacked_card_cannot_duel(db: Session):
    user = User(
        email=f"duel_{uuid.uuid4().hex[:8]}@test.com",
        nickname="duel",
        real_name_verified=True,
    )
    db.add(user)
    db.commit()
    card = CollectibleCard(
        code=f"duel_stack_{uuid.uuid4().hex[:6]}",
        name="Stack",
        rarity="common",
        series="test",
        active=True,
    )
    db.add(card)
    db.flush()
    row = UserCollectibleCard(user_id=user.id, card_id=card.id, count=2, source="test", star=1)
    db.add(row)
    db.commit()
    ids = _cards(db, user, 2)
    ids.append(row.id)
    with pytest.raises(BadRequestError, match="叠卡"):
        CardDuelService(db).challenge_ai(user, ids[:3], stake_points=0)


def test_pvp_challenge_and_accept(db: Session):
    challenger = User(
        email=f"ch_{uuid.uuid4().hex[:8]}@test.com",
        nickname="challenger",
        real_name_verified=True,
        invite_code=f"CH{uuid.uuid4().hex[:4].upper()}",
    )
    defender = User(
        email=f"df_{uuid.uuid4().hex[:8]}@test.com",
        nickname="defender",
        real_name_verified=True,
        redeem_points=200,
        invite_code=f"DF{uuid.uuid4().hex[:4].upper()}",
    )
    db.add_all([challenger, defender])
    db.commit()
    ch_cards = _cards(db, challenger)
    df_cards = _cards(db, defender)
    svc = CardDuelService(db)
    invite = svc.challenge_user(challenger, ch_cards, invite_code=defender.invite_code, stake_points=0)
    assert invite["ok"] is True
    pending = svc.pending_duels(defender)
    assert len(pending) == 1
    res = svc.accept_duel(defender, pending[0]["duel_id"], df_cards)
    assert res["ok"] is True
    assert "duel_id" in res


def test_duel_battalion_idempotent_per_duel(db: Session):
    from app.services.arena_service import ArenaService

    user = User(
        email=f"bt_{uuid.uuid4().hex[:8]}@test.com",
        nickname="bt",
        real_name_verified=True,
        battalion_points_season=0,
    )
    db.add(user)
    db.commit()
    arena = ArenaService(db)
    assert arena.apply_duel_win_reward(user, duel_id=101) > 0
    assert arena.apply_duel_win_reward(user, duel_id=101) == 0
    assert arena.apply_duel_win_reward(user, duel_id=102) > 0
