from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db
from app.db.models.commerce import User
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("/preview")
def referral_preview(code: str = Query(..., min_length=4, max_length=12), db: Session = Depends(get_db)):
    return ReferralService(db).preview_invite_code(code)

@router.get("/me")
def referral_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReferralService(db).get_my_stats(user)


@router.get("/invites")
def referral_invites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReferralService(db).list_my_invites(user)


@router.get("/rules")
def referral_rules(db: Session = Depends(get_db)):
    return ReferralService(db).get_rules()


@router.get("/leaderboard")
def referral_leaderboard(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    viewer = user.id if user else None
    return ReferralService(db).get_weekly_leaderboard(viewer_id=viewer)
