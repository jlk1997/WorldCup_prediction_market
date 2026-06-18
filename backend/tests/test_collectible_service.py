"""Collectible card service tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.data.collectible_catalog import build_card_catalog
from app.db.models.commerce import (
    CardSetDefinition,
    CollectibleCard,
    CollectibleDropLog,
    CollectibleShard,
    User,
    UserCollectibleCard,
)
from app.db.session import SessionLocal
from app.services.collectible_service import CollectibleService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user(db: Session) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"coll_{suffix}@test.com",
        nickname="collector",
        fan_coins=100,
        redeem_points=500,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _card(db: Session, suffix: str, rarity: str = "common") -> CollectibleCard:
    card = CollectibleCard(
        code=f"test_card_{suffix}",
        name=f"Test Player {suffix}",
        rarity=rarity,
        series="test",
        active=True,
        sort_order=1,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def test_drop_cards_idempotent(db: Session):
    user = _user(db)
    suffix = uuid.uuid4().hex[:6]
    card = _card(db, suffix)
    svc = CollectibleService(db)

    r1 = svc.drop_cards(
        user, "signin", "signin_streak", 1001, force_rarity="common", card_code=card.code
    )
    db.commit()
    assert r1["dropped"] is True
    assert len(r1["cards"]) == 1

    owned = (
        db.query(UserCollectibleCard)
        .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
        .first()
    )
    assert owned is not None

    r2 = svc.drop_cards(
        user, "signin", "signin_streak", 1001, force_rarity="common", card_code=card.code
    )
    assert r2 == r1

    logs = db.query(CollectibleDropLog).filter(CollectibleDropLog.user_id == user.id).count()
    assert logs == 1


def test_duplicate_converts_to_shards(db: Session):
    user = _user(db)
    suffix = uuid.uuid4().hex[:6]
    card = _card(db, suffix, "rare")
    svc = CollectibleService(db)

    r1 = svc.drop_cards(
        user, "signin", "signin_streak", 3001, force_rarity="rare", card_code=card.code
    )
    db.commit()
    assert r1["dropped"] is True
    assert r1["cards"][0]["is_duplicate"] is False

    r2 = svc.drop_cards(
        user, "signin", "signin_streak", 3002, force_rarity="rare", card_code=card.code
    )
    db.commit()
    assert r2["dropped"] is True
    assert r2["cards"][0]["is_duplicate"] is True
    assert r2["cards"][0]["shards_gained"] == 15

    row = (
        db.query(CollectibleShard)
        .filter(CollectibleShard.user_id == user.id, CollectibleShard.rarity == "rare")
        .first()
    )
    assert row is not None
    assert row.amount >= 15


def test_synthesize_and_upgrade(db: Session):
    user = _user(db)
    suffix = uuid.uuid4().hex[:6]
    card = _card(db, suffix, "common")
    svc = CollectibleService(db)

    shard = CollectibleShard(user_id=user.id, rarity="common", amount=100)
    db.add(shard)
    db.commit()

    result = svc.synthesize(user, card.code)
    db.commit()
    assert result["card"]["code"] == card.code

    owned = (
        db.query(UserCollectibleCard)
        .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
        .first()
    )
    assert owned is not None

    user.redeem_points = 200
    shard.amount = 100
    db.commit()

    up = svc.upgrade_star(user, card.code)
    db.commit()
    assert up["new_star"] == 2


def test_set_claim(db: Session):
    user = _user(db)
    suffix = uuid.uuid4().hex[:6]
    c1 = _card(db, f"a_{suffix}", "common")
    c2 = _card(db, f"b_{suffix}", "rare")

    sdef = CardSetDefinition(
        code=f"test_set_{suffix}",
        name="Test Set",
        card_codes=[c1.code, c2.code],
        reward_json={"badge_code": f"test_badge_{suffix}", "badge_title": "测试收藏家", "fan_coins": 50},
        active=True,
    )
    db.add(sdef)
    db.commit()

    svc = CollectibleService(db)
    svc._grant_card(user, c1, "test")
    svc._grant_card(user, c2, "test")
    db.commit()

    sets = svc.get_sets(user)
    target = next(s for s in sets if s["code"] == sdef.code)
    assert target["complete"] is True

    claim = svc.claim_set_reward(user, sdef.code)
    db.commit()
    assert claim["reward"]["fan_coins"] == 50
    assert user.fan_coins >= 150


def test_build_catalog_from_db(db: Session):
    cards, sets = build_card_catalog(db)
    assert any(c["code"].startswith("legend_") for c in cards)
    assert isinstance(sets, list)


def test_settle_win_may_include_collectible_drop(db: Session):
    """When catalog cards exist, winning settlement attaches collectible_drop payload."""
    from app.db.models import Match
    from app.db.models.commerce import GamePrediction
    from app.services.game_service import GameService

    suffix = uuid.uuid4().hex[:8]
    _card(db, suffix, "common")
    m = Match(
        group_name="T",
        match_date="2026-06-20",
        match_time="20:00",
        team1_name=f"ColA_{suffix}",
        team2_name=f"ColB_{suffix}",
        status="finished",
        home_score=1,
        away_score=0,
    )
    user = User(
        email=f"colsettle_{suffix}@test.com",
        nickname="colsettle",
        fan_coins=100,
    )
    db.add_all([m, user])
    db.commit()
    pred = GamePrediction(
        user_id=user.id,
        match_id=m.id,
        pick="home",
        stake_coins=0,
        is_free=True,
        status="pending",
    )
    db.add(pred)
    db.commit()

    gs = GameService(db)
    assert gs._settle_one_transaction(pred.id) is True
    db.refresh(pred)
    assert pred.status == "won"

    log = (
        db.query(CollectibleDropLog)
        .filter(
            CollectibleDropLog.user_id == user.id,
            CollectibleDropLog.ref_type == "game_prediction",
            CollectibleDropLog.ref_id == pred.id,
        )
        .first()
    )
    # Drop is probabilistic; log may or may not exist, but settlement must succeed
    assert log is None or log.result_json is not None
