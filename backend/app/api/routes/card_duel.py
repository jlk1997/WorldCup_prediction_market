"""卡牌对决 API。"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.rate_limit import rate_limit_card_duel
from app.db.models.commerce import User
from app.services.card_duel_service import CardDuelService

router = APIRouter(prefix="/api/card-duel", tags=["card-duel"])


class ChallengeRequest(BaseModel):
    card_ids: list[int] = Field(..., min_length=3, max_length=3)
    stake_points: int = Field(default=0, ge=0)


class ChallengeUserRequest(ChallengeRequest):
    defender_id: int | None = None
    invite_code: str | None = None


class AcceptRequest(BaseModel):
    card_ids: list[int] = Field(..., min_length=3, max_length=3)


def _rate_limit(user: User, request: Request) -> None:
    rate_limit_card_duel(user.id)


@router.get("/config")
def duel_config(db: Session = Depends(get_db)):
    return CardDuelService(db).duel_config()


@router.get("/eligible")
def eligible(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardDuelService(db).eligible_cards(user)}


@router.get("/pending")
def pending(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardDuelService(db).pending_duels(user)}


@router.get("/outgoing")
def outgoing(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardDuelService(db).outgoing_duels(user)}


@router.post("/challenge-ai")
def challenge_ai(
    body: ChallengeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(user, request)
    return CardDuelService(db).challenge_ai(user, body.card_ids, stake_points=body.stake_points)


@router.post("/challenge")
def challenge_user(
    body: ChallengeUserRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.defender_id and not body.invite_code:
        from app.core.exceptions import BadRequestError

        raise BadRequestError("请提供 defender_id 或 invite_code")
    _rate_limit(user, request)
    return CardDuelService(db).challenge_user(
        user,
        body.card_ids,
        defender_id=body.defender_id,
        invite_code=body.invite_code,
        stake_points=body.stake_points,
    )


@router.post("/{duel_id}/accept")
def accept_duel(
    duel_id: int,
    body: AcceptRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(user, request)
    return CardDuelService(db).accept_duel(user, duel_id, body.card_ids)


@router.post("/{duel_id}/cancel")
def cancel_duel(
    duel_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(user, request)
    return CardDuelService(db).cancel_duel(user, duel_id)


@router.get("/history")
def history(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardDuelService(db).history(user, limit=limit)}
