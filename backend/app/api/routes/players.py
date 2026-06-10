from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.common import PlayerBrief, PlayerDetailedOut
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.db.repositories.player_repository import PlayerRepository

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/players", response_model=list[PlayerBrief])
def get_players(
    team_id: int | None = Query(default=None),
    q: str | None = Query(default=None, description="Search by player name, team, or club"),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
):
    try:
        repo = PlayerRepository(db)
        if team_id:
            players = repo.list_by_team(team_id)
            if q:
                needle = q.strip().lower()
                players = [p for p in players if needle in (p.name or "").lower() or needle in (p.club or "").lower()]
            return [
                PlayerBrief(
                    id=p.id,
                    name=p.name,
                    position=p.position,
                    age=p.age,
                    jersey_number=None,
                    is_key_player=bool(p.is_starter),
                )
                for p in players
            ]
        rows = repo.list_all(limit=limit, q=q)
        return [
            PlayerBrief(
                id=p.id,
                name=p.name,
                team_name=team_name,
                position=p.position,
                age=p.age,
                jersey_number=None,
                is_key_player=bool(p.is_starter),
            )
            for p, team_name in rows
        ]
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(f"数据库连接或查询错误: {exc}") from exc


@router.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    try:
        row = PlayerRepository(db).get_by_id(player_id)
        if not row:
            raise NotFoundError("球员未找到")
        player, team_name = row
        data = PlayerDetailedOut.model_validate(player).model_dump()
        data["team_name"] = team_name
        return {"status": "success", "data": data}
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
