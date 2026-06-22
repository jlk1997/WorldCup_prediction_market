"""Collection Pass API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.rate_limit import rate_limit_collection_pass_spend
from app.db.models.commerce import User
from app.services.arena_service import _team_date_ref
from app.services.collection_pass_service import CollectionPassService
from app.services.collectible_service import CollectibleService

router = APIRouter(prefix="/api/collection-pass", tags=["collection-pass"])


class ClaimRequest(BaseModel):
    level: int = Field(..., ge=1, le=40)
    track: str = Field(..., pattern="^(free|premium)$")


class EventCheerRequest(BaseModel):
    team_id: int = Field(..., ge=1)


@router.get("/track-catalog")
def track_catalog(db: Session = Depends(get_db)):
    data = CollectionPassService(db).get_track_catalog()
    return JSONResponse(
        content=data,
        headers={"Cache-Control": "public, max-age=3600, stale-while-revalidate=600"},
    )


@router.get("/summary/lite")
def get_summary_lite(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = CollectionPassService(db)
    summary = svc.get_summary_lite(user)
    summary["events"] = svc.event_summary()
    summary["event_cheer_status"] = CollectibleService(db).event_cheer_status(user)
    return summary


@router.get("/summary")
def get_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = CollectionPassService(db)
    summary = svc.get_summary(user)
    summary["events"] = svc.event_summary()
    summary["event_cheer_status"] = CollectibleService(db).event_cheer_status(user)
    return summary


@router.post("/claim")
def claim_reward(body: ClaimRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectionPassService(db).claim_level_reward(user, body.level, body.track)
    db.commit()
    return result


@router.post("/claim-all")
def claim_all_rewards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectionPassService(db).claim_all_rewards(user)
    db.commit()
    return result


@router.post("/xp-boost")
def buy_xp_boost(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit_collection_pass_spend(user.id)
    result = CollectionPassService(db).buy_xp_boost(user)
    db.commit()
    return result


@router.get("/events")
def list_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"events": CollectionPassService(db).event_summary()}


@router.post("/event-cheer")
def event_cheer(body: EventCheerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit_collection_pass_spend(user.id)
    from datetime import date

    drop = CollectibleService(db).event_cheer_drop(user, body.team_id)
    already = bool(drop.get("already_claimed"))
    if not already:
        ref_id = _team_date_ref(body.team_id, date.today())
        CollectionPassService.hook_award(
            user, db, "event_cheer", "team_date", ref_id, action="cheer"
        )
    db.commit()
    return {"collectible_drop": drop, "already_claimed": already}
