"""Arena battalion / star heat API."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db
from app.core.rate_limit import rate_limit_arena_spend
from app.db.models.commerce import User
from app.services.arena_service import ArenaService

router = APIRouter(prefix="/api/arena", tags=["arena"])

Period = Literal["season", "daily", "weekly"]
StarScope = Literal["global", "my"]


class BoostStarRequest(BaseModel):
    player_id: int = Field(gt=0)


class BoostCheerExtraRequest(BaseModel):
    match_id: int = Field(gt=0)


class MatchdayRallyRequest(BaseModel):
    team_id: int | None = Field(default=None, gt=0)


class SpotCheerRequest(BaseModel):
    team_id: int = Field(gt=0)
    slogan_index: int = Field(default=0, ge=0, le=20)


@router.get("/overview")
def arena_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).get_overview(user)


@router.get("/team-rank")
def team_rank(
    team_id: int | None = Query(None, gt=0),
    period: Period = Query("season"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_team_battalion_leaderboard(team_id, period, limit)


@router.get("/team-supporters")
def team_supporters(
    team_id: int = Query(..., gt=0),
    period: Period = Query("season"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_team_supporter_leaderboard(team_id, period, limit)


@router.get("/spot-cheer")
def spot_cheer_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).get_spot_cheer_status(user)


@router.post("/spot-cheer")
def spot_cheer(body: SpotCheerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit_arena_spend(user.id)
    return ArenaService(db).spot_cheer(user, body.team_id, body.slogan_index)


@router.get("/match/{match_id}")
def match_arena(
    match_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_match_arena(match_id, user.id if user else None)


@router.get("/star-heat")
def star_heat(
    scope: StarScope = Query("global"),
    limit: int = Query(20, ge=1, le=50),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_star_heat_board(user, scope=scope, limit=limit)


@router.get("/star-accuracy")
def star_accuracy(
    player_id: int | None = Query(None, gt=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_star_accuracy_board(player_id, limit)


@router.get("/matchday-goal")
def matchday_goal(
    team_id: int | None = Query(None, gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ArenaService(db).get_matchday_goal(user, team_id)


@router.get("/today-matches")
def today_matches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ArenaService(db).get_today_matches(user)


@router.post("/boost/star")
def boost_star(body: BoostStarRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit_arena_spend(user.id)
    return ArenaService(db).boost_star(user, body.player_id)


@router.post("/boost/cheer-extra")
def boost_cheer_extra(
    body: BoostCheerExtraRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rate_limit_arena_spend(user.id)
    return ArenaService(db).boost_cheer_extra(user, body.match_id)


@router.post("/boost/matchday-rally")
def matchday_rally(
    body: MatchdayRallyRequest = MatchdayRallyRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit_arena_spend(user.id)
    return ArenaService(db).matchday_rally(user, body.team_id)
