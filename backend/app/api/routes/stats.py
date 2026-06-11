from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_db
from app.core.cache import cache_get, cache_set
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.db.models import Match, NewsArticle, Team
from app.db.repositories.team_repository import TeamRepository

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    cached = cache_get("stats:overview")
    if cached is not None:
        return cached
    try:
        team_count = db.scalar(select(func.count()).select_from(Team)) or 0
        match_count = db.scalar(select(func.count()).select_from(Match)) or 0
        live_count = db.scalar(
            select(func.count()).select_from(Match).where(Match.status == "live")
        ) or 0
        finished_count = db.scalar(
            select(func.count()).select_from(Match).where(Match.status == "finished")
        ) or 0
        news_count = db.scalar(select(func.count()).select_from(NewsArticle)) or 0
        payload = {
            "status": "success",
            "data": {
                "teams": team_count,
                "matches": match_count,
                "live_matches": live_count,
                "finished_matches": finished_count,
                "news_articles": news_count,
            },
        }
        cache_set("stats:overview", payload, ttl=60)
        return payload
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("/teams/compare")
def compare_teams(
    team1: str = Query(..., description="球队1中文名"),
    team2: str = Query(..., description="球队2中文名"),
    db: Session = Depends(get_db),
):
    try:
        repo = TeamRepository(db)
        t1 = repo.get_by_name(team1)
        t2 = repo.get_by_name(team2)
        if not t1:
            raise NotFoundError(f"球队 {team1} 未找到")
        if not t2:
            raise NotFoundError(f"球队 {team2} 未找到")

        def brief(team):
            return {
                "name": team.name,
                "fifa_ranking": team.fifa_ranking,
                "group_name": team.group_name,
                "coach": team.coach,
                "formation": team.formation,
                "total_value": team.total_value,
                "avg_age": float(team.avg_age) if team.avg_age else None,
            }

        return {
            "status": "success",
            "data": {
                "team1": brief(t1),
                "team2": brief(t2),
                "ranking_diff": (t2.fifa_ranking or 999) - (t1.fifa_ranking or 999),
            },
        }
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
