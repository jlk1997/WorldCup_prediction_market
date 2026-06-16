"""Leaderboard season settlement tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import LeaderboardSeasonAward, User
from app.db.session import SessionLocal
from app.services.leaderboard_service import LeaderboardService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_user(db: Session, **kwargs) -> User:
    email = f"lbs_{uuid.uuid4().hex[:12]}@example.com"
    user = User(email=email, nickname=f"fan_{uuid.uuid4().hex[:6]}", **kwargs)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_season_settle_awards_top_users(db: Session):
    # 极高分数，避免与库内其他用户抢榜
    base = 995_000_000 + (uuid.uuid4().int % 1_000_000)
    u1 = _make_user(db, season_points=base + 200)
    u2 = _make_user(db, season_points=base + 100)
    svc = LeaderboardService(db)
    result = svc.settle_season_board(season_key="test_season", force=False)
    db.commit()

    assert result["awarded"] >= 2
    awards = (
        db.query(LeaderboardSeasonAward)
        .filter(
            LeaderboardSeasonAward.season_key == "test_season",
            LeaderboardSeasonAward.user_id.in_([u1.id, u2.id]),
        )
        .all()
    )
    assert len(awards) >= 2
    top_award = next(a for a in awards if a.user_id == u1.id)
    assert top_award.coins_awarded > 0
    assert top_award.rank <= 10
    db.refresh(u1)
    assert u1.fan_coins >= top_award.coins_awarded


def test_season_settle_idempotent(db: Session):
    base = 994_000_000 + (uuid.uuid4().int % 1_000_000)
    user = _make_user(db, season_points=base + 500)
    svc = LeaderboardService(db)
    first = svc.settle_season_board(season_key="test_idem")
    db.commit()
    db.refresh(user)
    coins_after_first = user.fan_coins
    second = svc.settle_season_board(season_key="test_idem")
    assert second["skipped_existing"] >= 1
    assert second["awarded"] == 0
    db.refresh(user)
    assert user.fan_coins == coins_after_first
    assert first["awarded"] >= 1


def test_season_settle_dual_boards_separate_ledger(db: Session):
    """Points + redeem board awards must not collide on wallet ref_type."""
    base = 990_000_000 + (uuid.uuid4().int % 1_000_000)
    user = _make_user(db, season_points=base + 500, redeem_points=base + 400)
    svc = LeaderboardService(db)
    r1 = svc.settle_season_board(season_key="dual_board_test", board="points", force=False)
    r2 = svc.settle_season_board(season_key="dual_board_test", board="redeem_points", force=False)
    assert r1["awarded"] >= 1
    assert r2["awarded"] >= 1
    awards = (
        db.query(LeaderboardSeasonAward)
        .filter(
            LeaderboardSeasonAward.user_id == user.id,
            LeaderboardSeasonAward.season_key == "dual_board_test",
        )
        .all()
    )
    boards = {a.board for a in awards}
    assert "points" in boards
    assert "redeem_points" in boards
    db.refresh(user)
    assert user.fan_coins >= 300


def test_reward_tiers_configured(db: Session):
    tiers = LeaderboardService(db).get_reward_tiers()
    assert tiers["tiers"]
    assert tiers["tiers"][0]["coins"] > 0
