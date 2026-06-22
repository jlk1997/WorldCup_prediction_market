import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agents.orchestrator import MatchAnalysisOrchestrator
from app.agents.report_validator import compute_live_fingerprint
from app.agents.tools import AgentTools
from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.api.schemas.common import (
    AgentAnalyzeRequest,
    AgentAnalyzeResponse,
    AgentBatchInsightRequest,
    AgentInsightOut,
)
from app.core.config import get_settings
from app.core.exceptions import AppError, BadRequestError, ForbiddenError, NotFoundError, ServiceUnavailableError
from app.core.rate_limit import rate_limit_agent, rate_limit_insight
from app.db.models import AgentRun
from app.db.models.commerce import User
from app.db.repositories.agent_repository import AgentRepository
from app.services.agent_worker import run_agent_analyze
from app.services.ai_billing_service import AiBillingService

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _safe_public_error(exc: Exception, *, default: str = "服务暂时不可用，请稍后重试") -> str:
    if get_settings().production_mode:
        return default
    return str(exc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _enforce_force_refresh(user: User, db: Session) -> None:
    settings = get_settings()
    today = _utcnow().date().isoformat()
    from app.core.redis_client import get_redis_client

    r = get_redis_client()
    if r is not None:
        key = f"ai:force_refresh:{user.id}:{today}"
        try:
            count = r.incr(key)
            if count == 1:
                r.expire(key, 86400)
            if count > settings.ai_daily_force_refresh_limit:
                r.decr(key)
                raise BadRequestError(
                    f"今日 AI 强制刷新次数已用完（{settings.ai_daily_force_refresh_limit} 次/日）"
                )
            return
        except BadRequestError:
            raise
        except Exception:
            pass

    today_start = datetime.combine(_utcnow().date(), datetime.min.time())
    locked = db.query(User).filter(User.id == user.id).with_for_update().first()
    if not locked:
        raise BadRequestError("用户不存在")
    used = (
        db.query(AgentRun)
        .filter(
            AgentRun.user_id == locked.id,
            AgentRun.created_at >= today_start,
            AgentRun.force_refresh.is_(True),
        )
        .count()
    )
    if used >= settings.ai_daily_force_refresh_limit:
        raise BadRequestError(f"今日 AI 强制刷新次数已用完（{settings.ai_daily_force_refresh_limit} 次/日）")


@router.get("/billing-status")
def ai_billing_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AiBillingService(db).quota_status(user)


@router.get("/status")
def agent_status():
    """Public AI queue snapshot for frontend progress hints."""
    from app.core.ai_concurrency import llm_queue_depth

    settings = get_settings()
    depth = llm_queue_depth()
    waiting = max(0, depth.get("active", 0) - depth.get("limit", 1))
    return {
        "status": "success",
        "data": {
            "llm": depth,
            "waiting_estimate": waiting,
            "parallel_llm": settings.agent_parallel_llm,
        },
    }


@router.post("/billing-preview")
def ai_billing_preview(
    req: AgentAnalyzeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    repo = AgentRepository(db)
    tools = AgentTools(db)
    live = tools.get_live_match(req.team1_name, req.team2_name)
    live_fp = compute_live_fingerprint(live if live.get("found") else None)
    cache_kwargs = (
        {"max_age_minutes": settings.agent_cache_minutes_live}
        if req.mode == "live"
        else {"max_age_hours": settings.agent_cache_hours_pre_match}
    )
    cached_run = None
    if not req.force_refresh:
        cached_run = repo.find_recent(
            req.team1_name,
            req.team2_name,
            req.mode,
            live_fingerprint=live_fp if req.mode == "live" else None,
            **cache_kwargs,
        )
    cache_hit = bool(cached_run and cached_run.final_output)
    billing = AiBillingService(db)
    team_ids = billing.resolve_team_ids(req.team1_name, req.team2_name)
    decision = billing.preview(user, req.mode, req.force_refresh, cache_hit, team_ids=team_ids)
    payload = decision.to_dict()
    discount = billing.card_discount_pct(user, team_ids)
    payload["card_discount_pct"] = discount
    from app.services.agent_asset_context import AgentAssetContextService

    payload["asset_context"] = AgentAssetContextService(db).build(user, team_ids)
    return {"status": "success", "cache_hit": cache_hit, "data": payload}


@router.get("/asset-context")
def agent_asset_context(
    team1_name: str | None = Query(None),
    team2_name: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing = AiBillingService(db)
    team_ids = billing.resolve_team_ids(team1_name, team2_name) if team1_name and team2_name else set()
    ctx = AgentAssetContextService(db).build(user, team_ids or None)
    return {"status": "success", "data": ctx}


@router.post("/analyze", response_model=AgentAnalyzeResponse)
async def agent_analyze(
    req: AgentAnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate_limit_agent(request, user.id)
    if req.force_refresh:
        _enforce_force_refresh(user, db)
    try:
        result = await asyncio.to_thread(
            run_agent_analyze,
            req.team1_name,
            req.team2_name,
            req.mode,
            req.force_refresh,
            None,
            user.id,
        )
        return AgentAnalyzeResponse(**result)
    except AppError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(_safe_public_error(exc)) from exc


@router.post("/analyze/stream")
async def agent_analyze_stream(
    req: AgentAnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate_limit_agent(request, user.id)
    if req.force_refresh:
        _enforce_force_refresh(user, db)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def progress(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    async def run_analysis() -> None:
        try:
            result = await asyncio.to_thread(
                run_agent_analyze,
                req.team1_name,
                req.team2_name,
                req.mode,
                req.force_refresh,
                progress,
                user.id,
            )
            await queue.put({"type": "result", **result})
        except AppError as exc:
            await queue.put({"type": "error", "message": exc.message, "status_code": exc.status_code})
        except SQLAlchemyError as exc:
            await queue.put({"type": "error", "message": _safe_public_error(exc), "status_code": 503})
        except Exception as exc:
            await queue.put({"type": "error", "message": _safe_public_error(exc, default="分析失败，请稍后重试"), "status_code": 500})
        finally:
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_analysis())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False, default=str)}\n\n"
        finally:
            await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/insight")
def agent_insight(
    request: Request,
    team1: str = Query(..., min_length=1),
    team2: str = Query(..., min_length=1),
    mode: str = Query(default="pre_match"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate_limit_insight(request)
    settings = get_settings()
    tools = AgentTools(db)
    live = tools.get_live_match(team1, team2)
    live_fp = compute_live_fingerprint(live if live.get("found") else None)
    cache_kwargs = (
        {"max_age_minutes": settings.agent_cache_minutes_live}
        if mode == "live"
        else {"max_age_hours": settings.agent_cache_hours_pre_match}
    )

    repo = AgentRepository(db)
    run = repo.find_recent(
        team1,
        team2,
        mode,
        live_fingerprint=live_fp if mode == "live" else None,
        **cache_kwargs,
    )
    if not run or not run.final_output:
        return {"status": "success", "data": AgentInsightOut(has_data=False)}

    out = run.final_output
    wp = out.get("win_probability") or {}
    return {
        "status": "success",
        "data": AgentInsightOut(
            has_data=True,
            run_id=run.id,
            summary=(out.get("summary") or "")[:280],
            predicted_score=out.get("predicted_score") or out.get("score") or "-",
            confidence=float(run.confidence) if run.confidence else float(out.get("confidence", 0.7)),
            win_probability={
                "team1": float(wp.get("team1", 0.33)),
                "draw": float(wp.get("draw", 0.34)),
                "team2": float(wp.get("team2", 0.33)),
            },
            mode=run.mode,
            created_at=run.created_at,
        ),
    }


@router.get("/runs")
def list_agent_runs(
    team: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    q: str | None = Query(default=None, description="搜索球队名"),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = AgentRepository(db)
    runs = repo.list_runs(limit=limit, offset=offset, team=team, mode=mode, q=q, user_id=user.id)
    return {
        "status": "success",
        "data": [
            {
                "id": r.id,
                "team1": r.team1,
                "team2": r.team2,
                "mode": r.mode,
                "confidence": float(r.confidence) if r.confidence else None,
                "created_at": r.created_at,
            }
            for r in runs
        ],
    }


@router.post("/insights/batch")
def batch_agent_insights(
    req: AgentBatchInsightRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate_limit_insight(request)
    settings = get_settings()
    repo = AgentRepository(db)
    tools = AgentTools(db)
    results: dict[str, dict] = {}

    for pair in req.pairs[:20]:
        key = f"{pair.team1}|{pair.team2}"
        cache_kwargs = (
            {"max_age_minutes": settings.agent_cache_minutes_live}
            if pair.mode == "live"
            else {"max_age_hours": settings.agent_cache_hours_pre_match}
        )
        live_fp = None
        if pair.mode == "live":
            live = tools.get_live_match(pair.team1, pair.team2)
            live_fp = compute_live_fingerprint(live if live.get("found") else None)
        run = repo.find_recent(
            pair.team1,
            pair.team2,
            pair.mode,
            live_fingerprint=live_fp,
            **cache_kwargs,
        )
        if not run or not run.final_output:
            results[key] = AgentInsightOut(has_data=False).model_dump()
            continue
        out = run.final_output
        wp = out.get("win_probability") or {}
        results[key] = AgentInsightOut(
            has_data=True,
            run_id=run.id,
            summary=(out.get("summary") or "")[:120],
            predicted_score=out.get("predicted_score") or out.get("score") or "-",
            confidence=float(run.confidence) if run.confidence else float(out.get("confidence", 0.7)),
            win_probability={
                "team1": float(wp.get("team1", 0.33)),
                "draw": float(wp.get("draw", 0.34)),
                "team2": float(wp.get("team2", 0.33)),
            },
            mode=run.mode,
            created_at=run.created_at,
        ).model_dump()

    return {"status": "success", "data": results}


@router.get("/runs/{run_id}")
def get_agent_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orchestrator = MatchAnalysisOrchestrator(db)
    run = orchestrator.get_run(run_id)
    if not run:
        raise NotFoundError("分析记录未找到")
    if run.user_id and run.user_id != user.id:
        raise ForbiddenError("无权查看该分析记录")
    if not run.user_id:
        out = run.final_output or {}
        wp = out.get("win_probability") or {}
        return {
            "status": "success",
            "run_id": run.id,
            "mode": run.mode,
            "created_at": run.created_at,
            "public_cache": True,
            "data": AgentInsightOut(
                has_data=True,
                run_id=run.id,
                summary=(out.get("summary") or "")[:280],
                predicted_score=out.get("predicted_score") or out.get("score") or "-",
                confidence=float(run.confidence) if run.confidence else float(out.get("confidence", 0.7)),
                win_probability={
                    "team1": float(wp.get("team1", 0.33)),
                    "draw": float(wp.get("draw", 0.34)),
                    "team2": float(wp.get("team2", 0.33)),
                },
                mode=run.mode,
                created_at=run.created_at,
            ).model_dump(),
        }
    data = orchestrator._format_report(
        run.final_output or {},
        run.steps_json or [],
        run.team1 or "",
        run.team2 or "",
        run.mode or "pre_match",
    )
    return {
        "status": "success",
        "run_id": run.id,
        "mode": run.mode,
        "created_at": run.created_at,
        "validation_warnings": (run.final_output or {}).get("validation_warnings") or [],
        "data": data,
    }
