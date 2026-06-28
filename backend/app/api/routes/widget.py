"""B 端嵌入：AI 预测 Widget 数据接口（只读、无登录）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.insight_helpers import insight_from_run
from app.agents.tools import AgentTools
from app.agents.report_validator import compute_live_fingerprint
from app.api.deps import get_db
from app.core.config import get_settings
from app.db.repositories.agent_repository import AgentRepository

router = APIRouter(prefix="/api/widget", tags=["widget"])


@router.get("/predict")
def widget_predict(
    team1: str = Query(..., min_length=1),
    team2: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """公开 Widget：返回 AI 倾向摘要（缓存），供媒体/品牌嵌入。"""
    settings = get_settings()
    repo = AgentRepository(db)
    tools = AgentTools(db)
    live = tools.get_live_match(team1, team2)
    mode = "live" if live.get("found") else "pre_match"
    live_fp = compute_live_fingerprint(live if live.get("found") else None)
    cache_kwargs = (
        {"max_age_minutes": settings.agent_cache_minutes_live}
        if mode == "live"
        else {"max_age_hours": settings.agent_cache_hours_pre_match}
    )
    run = repo.find_recent(team1, team2, mode, live_fingerprint=live_fp, **cache_kwargs)
    if not run or not run.final_output:
        return {"status": "success", "data": {"has_data": False, "disclaimer": "仅供参考"}}
    insight = insight_from_run(run, team1=team1, team2=team2, summary_max=160)
    return {
        "status": "success",
        "data": {
            **insight.model_dump(),
            "disclaimer": "AI 分析仅供参考，不构成投注或投资建议。",
            "brand": "最后一舞 · 世界杯2026",
        },
    }
