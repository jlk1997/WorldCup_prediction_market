"""资产中心 hub / 挂牌建议 API 测试。"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.asset_hub_service import AssetHubService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user_card(db: Session) -> tuple[User, UserCollectibleCard, CollectibleCard]:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"hub_{suffix}@test.com",
        nickname=f"hub_{suffix}",
        redeem_points=2000,
        real_name_verified=True,
    )
    card = CollectibleCard(
        code=f"hub_card_{suffix}",
        name="Hub Test Card",
        rarity="rare",
        series="test",
        active=True,
    )
    db.add_all([user, card])
    db.flush()
    row = UserCollectibleCard(
        user_id=user.id,
        card_id=card.id,
        star=1,
        count=1,
        source="test",
        tradable=True,
        lock_state="none",
        serial_no=1,
    )
    db.add(row)
    db.commit()
    db.refresh(user)
    db.refresh(row)
    db.refresh(card)
    return user, row, card


def test_hub_summary_shape(db: Session):
    user, _row, _card = _user_card(db)
    summary = AssetHubService(db).hub_summary(user)
    assert "redeem_points" in summary
    assert "portfolio_value" in summary
    assert summary["redeem_points"] == 2000
    assert summary["duel_pending_incoming"] == 0
    assert summary["action_count"] >= 0


def test_listing_hint_bounds(db: Session):
    user, row, card = _user_card(db)
    hint = AssetHubService(db).listing_hint(user, row.id)
    assert hint["user_card_id"] == row.id
    assert hint["card_name"] == card.name
    assert hint["price_range"]["min"] <= hint["suggested_price"] <= hint["price_range"]["max"]
    assert hint["fee_pct"] == 8
    assert "disclaimer" in hint
