"""AVATA / 文昌链 integration tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.integrations.avata_client import AvataClient
from app.services.collectible_chain_service import CollectibleChainService, CHAIN_STATUS_MINTED, CHAIN_STATUS_PENDING


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


def test_avata_client_mock_create_account():
    client = AvataClient()
    resp = client.create_accounts(count=1, operation_id=f"test_{uuid.uuid4().hex[:8]}")
    assert resp["data"]["addresses"][0]["native_address"]


def test_avata_client_mock_mint_and_query():
    client = AvataClient()
    class_id = "mock_class_test"
    op = f"test_mint_{uuid.uuid4().hex[:8]}"
    client.mint_nft(
        class_id,
        name="Test Card",
        uri="https://example.com/meta.json",
        recipient="mockaddr",
        operation_id=op,
    )
    tx = client.query_tx(op)
    assert tx["data"]["status"] == 1
    assert tx["data"]["nft"]["mint"]["id"]


def test_chain_service_queue_and_process(db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"chain_{suffix}@test.com", nickname="chain")
    card = CollectibleCard(
        code=f"chain_card_{suffix}",
        name="Chain Test",
        rarity="common",
        series="test",
        active=True,
    )
    db.add_all([user, card])
    db.commit()
    db.refresh(user)
    db.refresh(card)

    row = UserCollectibleCard(user_id=user.id, card_id=card.id, source="test", star=1, count=1)
    db.add(row)
    db.commit()
    db.refresh(row)

    chain = CollectibleChainService(db)
    chain.queue_mint(user, row, card)
    db.commit()
    assert row.chain_status == CHAIN_STATUS_PENDING

    result = chain.process_pending()
    db.refresh(row)
    assert result["processed"] >= 1
    assert row.chain_status == CHAIN_STATUS_MINTED
    assert row.chain_nft_id
