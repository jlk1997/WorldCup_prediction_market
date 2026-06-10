"""Run agent analysis in a dedicated DB session (thread-safe)."""

from __future__ import annotations

from collections.abc import Callable

from app.agents.orchestrator import MatchAnalysisOrchestrator
from app.db.session import SessionLocal

ProgressCallback = Callable[[dict], None]


def run_agent_analyze(
    team1_name: str,
    team2_name: str,
    mode: str,
    force_refresh: bool,
    progress: ProgressCallback | None,
    user_id: int | None,
) -> dict:
    db = SessionLocal()
    try:
        orchestrator = MatchAnalysisOrchestrator(db)
        return orchestrator.analyze(
            team1_name,
            team2_name,
            mode,
            force_refresh,
            progress,
            user_id,
        )
    finally:
        db.close()
