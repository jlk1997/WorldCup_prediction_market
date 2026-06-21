"""Force refresh must bypass shared DB cache and inflight cache wait."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.agents.orchestrator import MatchAnalysisOrchestrator
from app.db.models import AgentRun
from app.db.session import SessionLocal
from app.services.ai_inflight import InflightAcquireResult


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _fake_cached_run() -> AgentRun:
    run = MagicMock(spec=AgentRun)
    run.final_output = {
        "summary": "cached summary",
        "win_probability": {"team1": 0.5, "draw": 0.25, "team2": 0.25},
        "confidence": 0.8,
        "predicted_score": "1-0",
    }
    run.steps_json = []
    run.id = 42
    return run


def test_analyze_without_force_refresh_returns_early_cache(db):
    orch = MatchAnalysisOrchestrator(db)
    cached = _fake_cached_run()
    with patch.object(orch.teams, "get_by_name", return_value=MagicMock()):
        with patch.object(orch.tools, "get_live_match", return_value={"found": False}):
            with patch.object(orch.agent_runs, "find_recent", return_value=cached):
                result = orch.analyze("TeamA", "TeamB", force_refresh=False)
    assert result["cached"] is True
    assert result["run_id"] == 42


def test_analyze_force_refresh_skips_cache_and_runs_fresh(db):
    from app.core.exceptions import ServiceUnavailableError
    from app.db.models.commerce import User
    from app.services.ai_billing_service import AiBillingService, BillingDecision

    user = User(email=f"fr_{uuid.uuid4().hex[:10]}@test.com", nickname="fr", fan_coins=100)
    db.add(user)
    db.commit()
    db.refresh(user)

    orch = MatchAnalysisOrchestrator(db)
    cached = _fake_cached_run()
    fake_billing = BillingDecision(
        charge_coins=0,
        used_free_quota=True,
        free_remaining=1,
        daily_free_limit=2,
        mode="pre_match",
        force_refresh=True,
    )
    with patch.object(orch.teams, "get_by_name", return_value=MagicMock()):
        with patch.object(orch.tools, "get_live_match", return_value={"found": False}):
            with patch.object(orch.agent_runs, "find_recent", return_value=cached):
                with patch("app.agents.orchestrator.try_acquire_lock", return_value="user-lock"):
                    with patch(
                        "app.agents.orchestrator.acquire_inflight_or_wait",
                        return_value=InflightAcquireResult(token="leader"),
                    ) as mock_acquire:
                        with patch.object(AiBillingService, "charge_before_llm", return_value=fake_billing):
                            with patch.object(orch, "_gather_facts", side_effect=RuntimeError("reached_llm")) as mock_gather:
                                with pytest.raises(ServiceUnavailableError):
                                    orch.analyze("TeamA", "TeamB", force_refresh=True, user_id=user.id)
    assert mock_acquire.called
    wait_fn = mock_acquire.call_args[0][1]
    assert wait_fn() is None
    assert mock_acquire.call_args[0][0].endswith(":force")
    mock_gather.assert_called_once()


def test_billing_preview_force_refresh_never_cache_hit(db):
    from app.core.config import get_settings
    from app.db.models.commerce import User
    from app.db.repositories.agent_repository import AgentRepository
    from app.services.ai_billing_service import AiBillingService

    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"force_{suffix}@test.com", nickname="fr", fan_coins=100)
    db.add(user)
    db.flush()
    db.add(
        AgentRun(
            team1=f"TeamOne{suffix}",
            team2=f"TeamTwo{suffix}",
            mode="pre_match",
            final_output={"summary": "old"},
            confidence=0.7,
            user_id=user.id,
        )
    )
    db.commit()

    settings = get_settings()
    repo = AgentRepository(db)
    cached_run = repo.find_recent(
        f"TeamOne{suffix}",
        f"TeamTwo{suffix}",
        "pre_match",
        max_age_hours=settings.agent_cache_hours_pre_match,
    )
    assert cached_run is not None

    svc = AiBillingService(db)
    preview_normal = svc.preview(user, "pre_match", False, cache_hit=True)
    preview_force = svc.preview(user, "pre_match", True, cache_hit=False)
    assert preview_normal.charge_coins == 0
    assert preview_force.force_refresh is True
    assert preview_force.charge_coins >= 0
