"""Tests for AI analysis job crash recovery."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import AiAnalysisJob, User
from app.db.session import SessionLocal
from app.services.ai_analysis_job_service import AiAnalysisJobService
from app.services.ai_billing_service import BillingDecision


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_user(db: Session, fan_coins: int = 200) -> User:
    user = User(email=f"job_{uuid.uuid4().hex[:10]}@example.com", nickname="job", fan_coins=fan_coins)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_recover_stale_job_refunds_coins(db: Session):
    user = _make_user(db, fan_coins=100)
    billing = BillingDecision(
        charge_coins=15,
        used_free_quota=False,
        free_remaining=0,
        daily_free_limit=2,
        mode="pre_match",
        force_refresh=False,
    )
    user.fan_coins = 85
    job = AiAnalysisJob(
        user_id=user.id,
        team1="A",
        team2="B",
        mode="pre_match",
        force_refresh=False,
        status="running",
        billing_json=billing.to_dict(),
        started_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30),
    )
    db.add(job)
    db.commit()

    recovered = AiAnalysisJobService(db).recover_stale_jobs(stale_minutes=15)
    db.refresh(user)
    db.refresh(job)

    assert recovered == 1
    assert job.status == "refunded"
    assert user.fan_coins == 115


def test_running_recent_job_not_recovered(db: Session):
    user = _make_user(db)
    job = AiAnalysisJob(
        user_id=user.id,
        team1="C",
        team2="D",
        mode="pre_match",
        status="running",
        billing_json={"charge_coins": 0, "used_free_quota": True, "free_remaining": 1, "daily_free_limit": 2, "mode": "pre_match", "force_refresh": False},
        started_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2),
    )
    db.add(job)
    db.commit()

    recovered = AiAnalysisJobService(db).recover_stale_jobs(stale_minutes=15)
    db.refresh(job)
    assert recovered == 0
    assert job.status == "running"
