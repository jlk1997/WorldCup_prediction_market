"""Build lightweight AgentInsight payloads from cached runs."""

from __future__ import annotations

from typing import Any

from app.agents.report_presenter import build_betting_guide
from app.api.schemas.common import AgentInsightOut

_PICK_TO_PREDICT = {"1": "home", "X": "draw", "2": "away"}


def extract_betting_pick(out: dict[str, Any], team1: str, team2: str, mode: str = "pre_match") -> tuple[str | None, str | None]:
    """Map AI 1/X/2 pick to predict hall home/draw/away."""
    raw = out.get("betting_pick") or out.get("betting_guide", {}).get("recommended_pick")
    if raw:
        code = str(raw).upper()
        if code in _PICK_TO_PREDICT:
            guide = build_betting_guide(out, team1, team2, mode)
            return _PICK_TO_PREDICT[code], guide.get("pick_label")
    guide = build_betting_guide(out, team1, team2, mode)
    code = guide.get("recommended_pick")
    return _PICK_TO_PREDICT.get(str(code)), guide.get("pick_label")


def insight_from_run(
    run: Any,
    *,
    team1: str,
    team2: str,
    summary_max: int = 280,
) -> AgentInsightOut:
    out = run.final_output or {}
    wp = out.get("win_probability") or {}
    betting_pick, pick_label = extract_betting_pick(out, team1, team2, run.mode or "pre_match")
    return AgentInsightOut(
        has_data=True,
        run_id=run.id,
        summary=(out.get("summary") or "")[:summary_max],
        predicted_score=out.get("predicted_score") or out.get("score") or "-",
        confidence=float(run.confidence) if run.confidence else float(out.get("confidence", 0.7)),
        win_probability={
            "team1": float(wp.get("team1", 0.33)),
            "draw": float(wp.get("draw", 0.34)),
            "team2": float(wp.get("team2", 0.33)),
        },
        betting_pick=betting_pick,
        pick_label=pick_label,
        mode=run.mode,
        created_at=run.created_at,
    )
