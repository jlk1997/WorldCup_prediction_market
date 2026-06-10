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
