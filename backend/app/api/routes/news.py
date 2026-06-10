from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth_deps import get_optional_user
from app.api.deps import get_db, require_manual_sync
from app.api.schemas.common import NewsArticleOut
from app.core.cache import cache_delete_prefix
from app.core.exceptions import ServiceUnavailableError
from app.db.models.commerce import User
from app.ingest.news_rss_service import NewsRssService
from app.services.news_service import NewsService

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[NewsArticleOut])
def list_news(
    team: str | None = Query(default=None),
    lang: str | None = Query(default=None, description="en | zh | all"),
    limit: int = Query(default=30, le=100),
    personalize: bool = Query(default=True, description="登录用户按主/副队优先排序"),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    try:
        rows = NewsService(db).list_articles(
            lang=lang,
            limit=limit,
            team=team,
            user=user,
            personalize=personalize,
        )
        return [NewsArticleOut.model_validate(r) for r in rows]
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("/stats")
def news_stats(db: Session = Depends(get_db)):
    """Counts by language for UI tabs."""
    from sqlalchemy import func

    from app.db.models import NewsArticle

    rows = db.query(NewsArticle.lang, func.count(NewsArticle.id)).group_by(NewsArticle.lang).all()
    counts = {lang: cnt for lang, cnt in rows}
    return {
        "en": counts.get("en", 0),
        "zh": counts.get("zh", 0),
        "total": sum(counts.values()),
    }


@router.post("/sync", dependencies=[Depends(require_manual_sync)])
def trigger_news_sync(db: Session = Depends(get_db)):
    try:
        result = NewsRssService(db).sync()
        cache_delete_prefix("news:list:")
        return {"status": "success", **result}
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    except Exception as exc:
        raise ServiceUnavailableError(f"RSS 同步失败: {exc}") from exc
