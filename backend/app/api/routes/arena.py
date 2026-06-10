"""Arena battalion / star heat API."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db
from app.db.models.commerce import User
from app.services.arena_service import ArenaService

router = APIRouter(prefix="/api/arena", tags=["arena"])


class BoostStarRequest(BaseModel):
    player_id: int


class BoostCheerExtraRequest(BaseModel):
    match_id: int


@router.get("/overview")
def arena_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).get_overview(user)


@router.get("/team-rank")
def team_rank(
    team_id: int | None = Query(None),
    period: str = Query("season"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_team_battalion_leaderboard(team_id, period, limit)


@router.get("/match/{match_id}")
def match_arena(
    match_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_match_arena(match_id, user.id if user else None)


@router.get("/star-heat")
def star_heat(
    scope: str = Query("global"),
    limit: int = Query(20, ge=1, le=50),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_star_heat_board(user, scope=scope, limit=limit)


@router.get("/star-accuracy")
def star_accuracy(
    player_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_star_accuracy_board(player_id, limit)


@router.get("/matchday-goal")
def matchday_goal(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).get_matchday_goal(user)


@router.post("/boost/star")
def boost_star(body: BoostStarRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).boost_star(user, body.player_id)


@router.post("/boost/cheer-extra")
def boost_cheer_extra(
    body: BoostCheerExtraRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ArenaService(db).boost_cheer_extra(user, body.match_id)


@router.post("/boost/matchday-rally")
def matchday_rally(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).matchday_rally(user)
