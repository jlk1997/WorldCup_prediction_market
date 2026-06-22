"""联名卡 seed 测试。"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.data.collab_catalog import COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL
from app.db.models.commerce import CollectibleCard, MintEvent
from app.db.session import SessionLocal
from app.services.collectible_service import CollectibleService
from app.services.primary_mint_service import PrimaryMintService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_seed_collab_cards_idempotent(db: Session):
    svc = CollectibleService(db)
    r1 = svc.seed_collab_cards()
    r2 = svc.seed_collab_cards()
    assert r1["created"] + r1["updated"] >= 0
    assert r2["created"] == 0
    rows = (
        db.query(CollectibleCard)
        .filter(CollectibleCard.series.in_([COLLAB_SERIES_CLUB, COLLAB_SERIES_KOL]))
        .count()
    )
    assert rows >= 1


def test_seed_collab_events_idempotent(db: Session):
    svc = PrimaryMintService(db)
    r1 = svc.seed_collab_events()
    r2 = svc.seed_collab_events()
    count = db.query(MintEvent).filter(MintEvent.competition == "Collab2026").count()
    assert count >= 1
    assert r2.get("created", 0) == 0
    assert r1.get("created", 0) >= 0
