from fastapi import APIRouter, Depends, Query

from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy.orm import Session



from app.api.deps import get_db, require_manual_sync

from app.api.schemas.common import ScheduleItem

from app.core.exceptions import ServiceUnavailableError
from app.core.cache import cache_delete, cache_get, cache_set
from app.db.repositories.match_repository import MatchRepository



router = APIRouter(prefix="/api", tags=["schedule"])



ROUND_ORDER = ["r32", "r16", "qf", "sf", "third", "final"]

ROUND_TITLES = {

    "r32": "三十二强",

    "r16": "十六强",

    "qf": "四分之一决赛",

    "sf": "半决赛",

    "third": "三四名决赛",

    "final": "决赛",

}





def _to_schedule_item(m) -> ScheduleItem:

    return ScheduleItem(

        id=m.id,

        group=m.group_name,

        date=m.match_date,

        time=m.match_time,

        team1=m.team1_name,

        team2=m.team2_name,

        stadium=m.stadium,

        status=m.status or "scheduled",

        home_score=m.home_score,

        away_score=m.away_score,

        minute=m.minute,

        period=m.period,

        is_live=m.status == "live",

    )





@router.get("/schedule", response_model=list[ScheduleItem])

def get_schedule(db: Session = Depends(get_db)):

    try:

        cached = cache_get("schedule:all")
        if cached is not None:
            return cached

        matches = MatchRepository(db).list_schedule(limit=512)

        payload = [_to_schedule_item(m).model_dump() for m in matches]
        cache_set("schedule:all", payload, ttl=60)
        return payload

    except SQLAlchemyError as exc:

        raise ServiceUnavailableError(f"从数据库读取赛程失败: {exc}") from exc





@router.get("/schedule/bracket")

def get_knockout_bracket(db: Session = Depends(get_db)):

    """Knockout rounds grouped for bracket UI."""

    try:
        cached = cache_get("schedule:bracket")
        if cached is not None:
            return cached

        repo = MatchRepository(db)

        grouped = repo.list_knockout_bracket()

        rounds = []

        for key in ROUND_ORDER:

            items = grouped.get(key, [])

            if not items:

                continue

            rounds.append({

                "round": key,

                "title": ROUND_TITLES.get(key, key),

                "matches": [_to_schedule_item(m).model_dump() for m in items],

            })

        payload = {"status": "success", "data": {"rounds": rounds, "total": sum(len(r["matches"]) for r in rounds)}}
        cache_set("schedule:bracket", payload, ttl=60)
        return payload

    except SQLAlchemyError as exc:

        raise ServiceUnavailableError(str(exc)) from exc





@router.post("/schedule/resolve-bracket", dependencies=[Depends(require_manual_sync)])
def resolve_knockout_bracket(db: Session = Depends(get_db)):
    """Fill knockout placeholders from group standings and finished KO results."""
    from app.services.knockout_resolver import KnockoutResolverService
    from app.ingest.quota import invalidate_live_cache

    try:
        result = KnockoutResolverService(db).resolve()
        invalidate_live_cache()
        cache_delete("schedule:bracket")
        cache_delete("schedule:standings:local")
        cache_delete("schedule:all")
        cache_delete("stats:overview")
        return {"status": "success", **result}
    except Exception as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("/schedule/standings")
def get_group_standings(source: str = "local", db: Session = Depends(get_db)):
    from app.services.knockout_resolver import KnockoutResolverService
    from app.ingest.standings_sync_service import StandingsSyncService

    try:
        if source == "bsd":
            svc = StandingsSyncService()
            cached = svc.get_cached()
            if cached:
                return {"status": "success", "data": cached}
            return {
                "status": "success",
                "data": KnockoutResolverService(db).get_standings_payload(),
                "note": "积分榜缓存未就绪，已返回本地数据；后台将自动同步",
            }
        cached = cache_get("schedule:standings:local")
        if cached is not None:
            return cached
        payload = {"status": "success", "data": KnockoutResolverService(db).get_standings_payload()}
        cache_set("schedule:standings:local", payload, ttl=60)
        return payload
    except SQLAlchemyError:
        raise ServiceUnavailableError("积分榜数据暂不可用") from None


@router.post("/schedule/expand", dependencies=[Depends(require_manual_sync)])
def expand_local_schedule():
    """Generate 104 matches locally from WorldCup2026_Teams groups."""
    from app.db.session import SessionLocal
    from scripts.expand_schedule import apply_to_db, generate_schedule
    from app.services.knockout_resolver import KnockoutResolverService
    from app.ingest.quota import invalidate_live_cache

    try:
        matches = generate_schedule()
        count = apply_to_db(matches)
        db = SessionLocal()
        try:
            KnockoutResolverService(db).resolve()
        finally:
            db.close()
        invalidate_live_cache()
        cache_delete("schedule:bracket")
        cache_delete("schedule:standings:local")
        cache_delete("schedule:all")
        cache_delete("stats:overview")
        return {"status": "success", "matches": count}
    except Exception as exc:
        raise ServiceUnavailableError(str(exc)) from exc


