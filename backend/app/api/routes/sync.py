from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_secret_in_production, require_manual_sync
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.db.repositories.match_repository import SyncLogRepository
from app.ingest.live_sync_service import LiveMatchSyncService
from app.ingest.news_rss_service import NewsRssService

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/status", dependencies=[Depends(require_admin_secret_in_production)])
def sync_status(db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        logs = SyncLogRepository(db).list_recent(10)
        return {
            "status": "success",
            "logs": [
                {
                    "source": log.source,
                    "status": log.status,
                    "records": log.records,
                    "error": None if settings.production_mode else log.error,
                    "ran_at": log.ran_at,
                }
                for log in logs
            ],
        }
    except SQLAlchemyError:
        raise ServiceUnavailableError("同步状态暂不可用") from None


@router.get("/health", dependencies=[Depends(require_admin_secret_in_production)])
def sync_health(db: Session = Depends(get_db)):
    """Operational metrics for match sync and pending predictions."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from app.core.match_kickoff import parse_kickoff
    from app.db.models import Match
    from app.db.models.commerce import GamePrediction

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    unlinked = db.scalar(
        select(func.count()).select_from(Match).where(Match.external_fixture_id.is_(None))
    ) or 0
    stale_scheduled = 0
    for m in db.scalars(select(Match).where(Match.status == "scheduled")).all():
        kick = parse_kickoff(m)
        if kick and kick <= now and m.external_fixture_id:
            stale_scheduled += 1
    pending_old = (
        db.query(func.count(GamePrediction.id))
        .join(Match, GamePrediction.match_id == Match.id)
        .filter(
            GamePrediction.status == "pending",
            Match.status == "finished",
        )
        .scalar()
    ) or 0
    pending_stuck = (
        db.query(func.count(GamePrediction.id))
        .filter(
            GamePrediction.status == "pending",
            GamePrediction.created_at < now - timedelta(hours=24),
        )
        .scalar()
    ) or 0
    return {
        "status": "ok",
        "unlinked_matches": unlinked,
        "stale_scheduled": stale_scheduled,
        "pending_finished_matches": pending_old,
        "pending_older_than_24h": pending_stuck,
    }


@router.post("/run", dependencies=[Depends(require_manual_sync)])
def sync_run_all(db: Session = Depends(get_db)):
    try:
        live = LiveMatchSyncService(db).sync()
        news = NewsRssService(db).sync()
        settled = voided = 0
        try:
            from app.services.game_service import GameService

            result = GameService(db).settle_all_pending()
            settled = result.get("settled", 0)
            voided = result.get("voided", 0)
        except Exception:
            pass
        return {
            "status": "success",
            "live_updated": live,
            "news_inserted": news,
            "predictions_settled": settled,
            "predictions_voided": voided,
        }
    except SQLAlchemyError:
        raise ServiceUnavailableError("同步任务失败，请稍后重试") from None
