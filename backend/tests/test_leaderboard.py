"""Leaderboard service tests."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.models.commerce import GamePrediction, User
from app.db.repositories.user_repository import WalletRepository
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
    email = f"lb_{uuid.uuid4().hex[:12]}@example.com"
    user = User(email=email, nickname=f"fan_{uuid.uuid4().hex[:6]}", **kwargs)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_match(db: Session) -> Match:
    m = Match(team1_name="A", team2_name="B", status="finished", home_score=1, away_score=0)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_season_points_board_rank(db: Session):
    # 使用极高分数避免与库内其他测试用户冲突
    base = 90_000_000 + (uuid.uuid4().int % 10_000_000)
    u1 = _make_user(db, season_points=base)
    u2 = _make_user(db, season_points=base + 100)
    svc = LeaderboardService(db)
    board = svc.get_points_board("season", limit=50)
    assert board["metric"] == "season_points"
    top_ids = [r["user_id"] for r in board["rows"]]
    assert u2.id in top_ids
    assert svc._season_points_rank(u2) <= svc._season_points_rank(u1)


def test_daily_board_uses_point_ledger(db: Session):
    user = _make_user(db, season_points=0)
    WalletRepository(db).add_points(user, 40, "predict_win")
    db.commit()
    board = LeaderboardService(db).get_points_board("daily", limit=20, viewer_id=user.id)
    me_rows = [r for r in board["rows"] if r["user_id"] == user.id]
    assert me_rows
    assert me_rows[0]["points"] == 40
    assert me_rows[0]["is_me"] is True


def test_predict_accuracy_board_min_samples(db: Session):
    user = _make_user(db)
    for i in range(5):
        m = _make_match(db)
        db.add(
            GamePrediction(
                user_id=user.id,
                match_id=m.id,
                pick="home",
                status="won" if i < 4 else "lost",
                points_awarded=30 if i < 4 else 0,
            )
        )
    db.commit()
    board = LeaderboardService(db).get_predict_accuracy_board(min_samples=5, viewer_id=user.id)
    me = next((r for r in board["rows"] if r["user_id"] == user.id), None)
    assert me is not None
    assert me["win_rate"] == 80.0


def test_duel_elo_board(db: Session):
    u1 = _make_user(db, duel_elo=1200)
    u2 = _make_user(db, duel_elo=1300)
    svc = LeaderboardService(db)
    board = svc.get_duel_board(by="elo", limit=20, viewer_id=u1.id)
    assert board["board"] == "duel_elo"
    ids = [r["user_id"] for r in board["rows"]]
    assert u2.id in ids
    me = next(r for r in board["rows"] if r["user_id"] == u1.id)
    assert me["is_me"] is True
    assert me["tier_label"]
