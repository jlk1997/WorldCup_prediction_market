from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_manual_sync
from app.api.schemas.common import LiveMatchOut
from app.core.cache import cache_get, cache_set
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.db.repositories.match_repository import MatchRepository, SyncLogRepository
from app.ingest.live_sync_service import LiveMatchSyncService
from app.ingest.quota import get_usage

router = APIRouter(prefix="/api/live", tags=["live"])


def _to_live_item(m) -> LiveMatchOut:
    return LiveMatchOut(
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
        events=m.events_json,
        live_updated_at=m.live_updated_at,
    )


@router.get("/matches", response_model=list[LiveMatchOut])
def list_live_matches(db: Session = Depends(get_db)):
    try:
        cached = cache_get("live:matches:full")
        if cached:
            return cached
        repo = MatchRepository(db)
        payload = [_to_live_item(m).model_dump() for m in repo.list_schedule()]
        cache_set("live:matches:full", payload, ttl=30)
        return payload
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("/quota")
def api_quota():
    return {"status": "success", "data": get_usage("bsd")}


@router.get("/grouped")
def grouped_matches(db: Session = Depends(get_db)):
    try:
        cached = cache_get("live:grouped")
        if cached:
            return cached
        grouped = MatchRepository(db).list_by_status()
        result = {"status": "success", "data": {}}
        data = {}
        for status, matches in grouped.items():
            data[status] = [_to_live_item(m).model_dump() for m in matches]
        result["data"] = data
        cache_set("live:grouped", result, ttl=30)
        return result
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("/match/{match_id}", response_model=LiveMatchOut)
def get_live_match(match_id: int, db: Session = Depends(get_db)):
    try:
        match = MatchRepository(db).get_by_id(match_id)
        if not match:
            raise NotFoundError("比赛未找到")
        return _to_live_item(match)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.post("/sync", dependencies=[Depends(require_manual_sync)])
def trigger_live_sync(db: Session = Depends(get_db)):
    try:
        count = LiveMatchSyncService(db).sync()
        logs = SyncLogRepository(db).list_recent(1)
        return {"status": "success", "updated": count, "last_log": logs[0].status if logs else None}
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.post("/import-fixtures", dependencies=[Depends(require_manual_sync)])
def import_fixtures(db: Session = Depends(get_db), max_matches: int = 104):
    try:
        count = LiveMatchSyncService(db).link_fixtures()
        return {"status": "success", "linked": count, "imported": count}
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.post("/link-bsd", dependencies=[Depends(require_manual_sync)])
def link_bsd_events(db: Session = Depends(get_db)):
    try:
        count = LiveMatchSyncService(db).link_fixtures()
        return {"status": "success", "linked": count}
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
