"""Chain provenance and pending expiry tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.collectible_chain_service import (
    CHAIN_STATUS_FAILED,
    CHAIN_STATUS_NONE,
    CollectibleChainService,
)
from app.services.collectible_service import CollectibleService


@pytest.fixture(autouse=True)
def avata_mock_env(monkeypatch):
    monkeypatch.setenv("AVATA_ENABLED", "true")
    monkeypatch.setenv("AVATA_MOCK", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_provenance_includes_mint_event(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"prov_{suffix}@test.com", nickname="prov")
    card = CollectibleCard(
        code=f"prov_card_{suffix}",
        name="Prov Card",
        rarity="common",
        series="test",
        active=True,
    )
    db.add_all([user, card])
    db.flush()
    row = UserCollectibleCard(
        user_id=user.id,
        card_id=card.id,
        source="predict_win",
        star=1,
        count=1,
        chain_status="minted",
        chain_nft_id="nft_test",
        chain_tx_hash="tx_test_hash",
    )
    db.add(row)
    db.commit()

    prov = CollectibleService(db).get_provenance(user, row.id)
    assert prov["user_card_id"] == row.id
    kinds = [e["kind"] for e in prov["events"]]
    assert "obtained" in kinds
    assert "mint" in kinds
    assert any(e.get("tx_hash") == "tx_test_hash" for e in prov["events"] if e["kind"] == "mint")


def test_expire_stale_pending(db: Session, monkeypatch):
    from datetime import timedelta

    from app.services.collectible_chain_service import CHAIN_STATUS_PENDING, _utcnow

    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"exp_{suffix}@test.com", nickname="exp")
    card = CollectibleCard(
        code=f"exp_card_{suffix}",
        name="Exp",
        rarity="common",
        series="test",
        active=True,
    )
    db.add_all([user, card])
    db.flush()
    row = UserCollectibleCard(
        user_id=user.id,
        card_id=card.id,
        source="test",
        star=1,
        count=1,
        chain_status=CHAIN_STATUS_PENDING,
    )
    db.add(row)
    db.commit()
    from sqlalchemy import update

    db.execute(
        update(UserCollectibleCard)
        .where(UserCollectibleCard.id == row.id)
        .values(updated_at=_utcnow() - timedelta(minutes=60))
    )
    db.commit()

    chain = CollectibleChainService(db)
    n = chain._expire_stale_pending()
    assert n >= 1
    db.commit()
    db.refresh(row)
    assert row.chain_status == CHAIN_STATUS_FAILED
    assert row.chain_error == "mint_timeout"


def test_retry_allowed_for_none(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"retry_{suffix}@test.com", nickname="retry")
    card = CollectibleCard(
        code=f"retry_card_{suffix}",
        name="Retry",
        rarity="common",
        series="test",
        active=True,
    )
    db.add_all([user, card])
    db.flush()
    row = UserCollectibleCard(
        user_id=user.id,
        card_id=card.id,
        source="test",
        star=1,
        count=1,
        chain_status=CHAIN_STATUS_NONE,
    )
    db.add(row)
    db.commit()

    result = CollectibleChainService(db).retry_mint(user, row.id)
    db.commit()
    assert result.get("status") in ("minted", "minting", "pending", "failed")
