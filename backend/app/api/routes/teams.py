from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.common import PlayerDetailedOut, ScheduleItem, TeamBrief, TeamDetail, TeamDetailResponse
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.db.models import PlayerDetailed, Team
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.team_repository import TeamRepository
from app.utils.team_names import canonical_team_name, display_team_name

router = APIRouter(prefix="/api", tags=["teams"])


def _sort_players(players: list[PlayerDetailed]) -> list[PlayerDetailed]:
    order = {"门将": 1, "后卫": 2, "中场": 3, "前锋": 4}

    def key(p: PlayerDetailed):
        return (order.get(p.position or "", 5), 0 if p.is_starter else 1)

    return sorted(players, key=key)


def _to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _team_to_detail(team: Team, players: list[PlayerDetailed]) -> TeamDetail:
    return TeamDetail(
        id=team.id,
        name=team.name,
        country_code=team.country_code,
        group_name=team.group_name,
        fifa_ranking=team.fifa_ranking,
        total_value=team.total_value,
        avg_age=_to_float(team.avg_age),
        coach=team.coach,
        formation=team.formation,
        logo_url=team.logo_url,
        founded=team.founded,
        city=team.city,
        stadium=team.stadium,
        capacity=team.capacity,
        players=[PlayerDetailedOut.model_validate(p) for p in players],
    )


@router.get("/teams", response_model=list[TeamBrief])
def get_teams(db: Session = Depends(get_db)):
    try:
        teams = TeamRepository(db).list_all()
        return teams
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(f"数据库连接或查询错误: {exc}") from exc


@router.get("/team/{team_name}", response_model=TeamDetailResponse)
def get_team_info(team_name: str, db: Session = Depends(get_db)):
    try:
        canonical = canonical_team_name(team_name)
        team = TeamRepository(db).get_by_name(canonical) or TeamRepository(db).get_by_name(team_name)
        if not team:
            raise NotFoundError(f"球队 {team_name} 未找到")
        players = _sort_players(team.players_detailed or [])
        detail = _team_to_detail(team, players)
        if team.name != display_team_name(team.name):
            detail.name = display_team_name(team.name)
        return TeamDetailResponse(data=detail)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(f"Error fetching team info: {exc}") from exc


@router.get("/team/{team_name}/matches")
def get_team_matches(
    team_name: str,
    limit: int = Query(default=10, le=30),
    db: Session = Depends(get_db),
):
    try:
        canonical = canonical_team_name(team_name)
        team = TeamRepository(db).get_by_name(canonical) or TeamRepository(db).get_by_name(team_name)
        if not team:
            raise NotFoundError(f"球队 {team_name} 未找到")
        matches = MatchRepository(db).list_for_team(team.name, limit=limit)
        return {
            "status": "success",
            "data": [
                ScheduleItem(
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
                for m in matches
            ],
        }
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
