"""Tests for collectible share tokens and pages."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.share_page_service import SharePageService
from app.services.share_token import make_collectible_share_token, parse_collectible_share_token


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_collectible_share_token_roundtrip():
    secret = "test-secret"
    token = make_collectible_share_token(7, "legend_ronaldo", secret)
    parsed = parse_collectible_share_token(token, secret)
    assert parsed == (7, "legend_ronaldo")
    assert parse_collectible_share_token(token, "wrong") is None
    assert parse_collectible_share_token("bad.token.here", secret) is None


def test_collectible_share_page_owned(client, db: Session):
    from app.core.config import get_settings

    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"col_share_{suffix}@test.com", nickname="藏品测试", fan_coins=0, invite_code=f"C{suffix[:7].upper()}")
    db.add(user)
    db.flush()
    card = CollectibleCard(
        code=f"test_card_{suffix}",
        name="测试球星",
        rarity="legend",
        series="legend",
        image_url="/legends/test.webp",
        active=True,
    )
    db.add(card)
    db.flush()
    db.add(
        UserCollectibleCard(
            user_id=user.id,
            card_id=card.id,
            star=3,
            count=1,
            source="predict_win",
        )
    )
    db.commit()

    settings = get_settings()
    token = make_collectible_share_token(user.id, card.code, settings.jwt_secret)
    r = client.get(f"/share/collectible/{token}")
    assert r.status_code == 200
    assert "藏品测试" in r.text or "藏**" in r.text
    assert "测试球星" in r.text
    assert "legend" not in r.text.lower() or "传奇" in r.text
    assert f"highlight={card.code}" in r.text


def test_collectible_share_page_unowned(client, db: Session):
    from app.core.config import get_settings

    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"col_unowned_{suffix}@test.com", nickname="收集者", fan_coins=0)
    db.add(user)
    db.flush()
    card = CollectibleCard(
        code=f"unowned_{suffix}",
        name="未获得卡",
        rarity="epic",
        series="legend",
        active=True,
    )
    db.add(card)
    db.commit()

    settings = get_settings()
    token = make_collectible_share_token(user.id, card.code, settings.jwt_secret)
    svc = SharePageService(db, settings)
    meta = svc.collectible_share_page(token)
    assert meta is not None
    assert "正在收集" in meta["title"]
    assert "未获得卡" in meta["title"]
