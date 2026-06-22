"""足球数字资产平台 — 交易行/流通合规关键路径测试。"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.marketplace_service import MarketplaceService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user_card(db: Session, *, count: int = 1, redeem: int = 5000) -> tuple[User, UserCollectibleCard, CollectibleCard]:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"asset_{suffix}@test.com",
        nickname=f"asset_{suffix}",
        redeem_points=redeem,
        real_name_verified=True,
    )
    card = CollectibleCard(
        code=f"asset_card_{suffix}",
        name="Asset Test Card",
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
        count=count,
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


def test_stacked_card_cannot_list(db: Session):
    user, row, _card = _user_card(db, count=2)
    svc = MarketplaceService(db)
    with pytest.raises(BadRequestError, match="叠卡"):
        svc.create_listing(user, row.id, list_type="fixed", price_points=100)


def test_auction_same_bidder_can_raise_bid(db: Session):
    seller, srow, _ = _user_card(db, redeem=0)
    buyer, _brow, _ = _user_card(db, redeem=5000)
    buyer.real_name_verified = True
    seller.real_name_verified = True
    db.commit()

    mkt = MarketplaceService(db)
    listing = mkt.create_listing(seller, srow.id, list_type="auction", price_points=100)
    lid = listing["listing_id"]

    r1 = mkt.place_bid(buyer, lid, 100)
    assert r1["current_bid"] == 100
    buyer = db.get(User, buyer.id)
    assert buyer.redeem_points == 4900

    r2 = mkt.place_bid(buyer, lid, 120)
    assert r2["current_bid"] == 120
    buyer = db.get(User, buyer.id)
    assert buyer.redeem_points == 4880


def test_fixed_price_buy_transfers_card(db: Session):
    seller, srow, _card = _user_card(db, redeem=0)
    buyer, _brow, _ = _user_card(db, redeem=5000)
    seller.real_name_verified = True
    buyer.real_name_verified = True
    db.commit()

    mkt = MarketplaceService(db)
    lid = mkt.create_listing(seller, srow.id, list_type="fixed", price_points=200)["listing_id"]
    mkt.buy_now(buyer, lid)

    row = db.get(UserCollectibleCard, srow.id)
    assert row is not None
    assert row.user_id == buyer.id
    buyer = db.get(User, buyer.id)
    seller = db.get(User, seller.id)
    assert buyer.redeem_points == 4800
    assert seller.redeem_points > 0


def test_fixed_listing_expires_unlocks_card(db: Session):
    from datetime import datetime, timedelta, timezone

    from app.db.models.commerce import CardListing

    user, row, _ = _user_card(db)
    user.real_name_verified = True
    db.commit()

    mkt = MarketplaceService(db)
    lid = mkt.create_listing(user, row.id, list_type="fixed", price_points=150, duration_hours=1)["listing_id"]
    listing = db.get(CardListing, lid)
    listing.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()

    result = mkt.expire_stale_listings()
    assert result["expired"] == 1
    row = db.get(UserCollectibleCard, row.id)
    assert row.lock_state == "none"
    listing = db.get(CardListing, lid)
    assert listing.status == "expired"


def test_buyback_adds_redeem_points(db: Session):
    from app.services.card_transfer_service import CardTransferService

    user, row, _card = _user_card(db, redeem=100)
    user.real_name_verified = True
    db.commit()
    before = user.redeem_points
    res = CardTransferService(db).buyback(user, row.id)
    user = db.get(User, user.id)
    assert res["points_gained"] > 0
    assert user.redeem_points == before + res["points_gained"]
    assert db.get(UserCollectibleCard, row.id) is None


def test_split_stack_creates_tradable_rows(db: Session):
    from app.services.card_asset_service import CardAssetService

    user, row, _ = _user_card(db, count=3)
    svc = CardAssetService(db)
    res = svc.split_stack(user, row.id, amount=2)
    db.commit()
    assert res["split_count"] == 2
    assert res["remaining_stack"] == 1
    row = db.get(UserCollectibleCard, row.id)
    assert row.count == 1
    new_rows = db.query(UserCollectibleCard).filter(UserCollectibleCard.user_id == user.id).all()
    assert len(new_rows) == 3
    singles = [r for r in new_rows if r.id != row.id]
    assert len(singles) == 2
    for s in singles:
        assert s.count == 1
        assert s.serial_no is not None
