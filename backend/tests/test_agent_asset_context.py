"""Agent 资产上下文测试。"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.db.session import SessionLocal
from app.services.agent_asset_context import AgentAssetContextService
from app.services.ai_billing_service import AiBillingService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_agent_asset_context_basic(db: Session):
    user = User(
        email=f"ctx_{uuid.uuid4().hex[:8]}@test.com",
        nickname="ctx",
        redeem_points=100,
        fan_coins=50,
        real_name_verified=True,
    )
    db.add(user)
    db.commit()
    ctx = AgentAssetContextService(db).build(user)
    assert ctx["redeem_points"] == 100
    assert ctx["fan_coins"] == 50
    assert ctx["cards_owned"] == 0
    assert "disclaimer" in ctx


def test_card_discount_in_context(db: Session):
    from app.db.models import Team

    team = db.query(Team).first()
    if not team:
        pytest.skip("no teams")
    user = User(
        email=f"ctx2_{uuid.uuid4().hex[:8]}@test.com",
        nickname="ctx2",
    )
    db.add(user)
    db.flush()
    card = CollectibleCard(
        code=f"ctx_{uuid.uuid4().hex[:6]}",
        name="Team Card",
        rarity="rare",
        series="team_squad",
        team_id=team.id,
        active=True,
    )
    db.add(card)
    db.flush()
    db.add(UserCollectibleCard(user_id=user.id, card_id=card.id, star=1, count=1, source="test"))
    db.commit()
    team_ids = {team.id}
    discount = AiBillingService(db).card_discount_pct(user, team_ids)
    ctx = AgentAssetContextService(db).build(user, team_ids)
    assert ctx["match_team_cards"] == 1
    assert ctx["card_discount_pct"] == round(discount * 100, 1)
