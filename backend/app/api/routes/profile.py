from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db
from app.api.schemas.profile import ProfilePatchRequest, ProfileSetupRequest
from app.db.models.commerce import User
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/status")
def profile_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProfileService(db).get_status(user)


@router.get("/teams")
def profile_teams(db: Session = Depends(get_db)):
    return ProfileService(db).list_teams()


@router.get("/players")
def profile_players(team_ids: str = Query(..., description="comma-separated team ids"), db: Session = Depends(get_db)):
    ids = [int(x.strip()) for x in team_ids.split(",") if x.strip().isdigit()]
    return ProfileService(db).list_players_for_teams(ids)


@router.put("/setup")
def profile_setup(body: ProfileSetupRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProfileService(db).setup_profile(
        user, body.main_team_id, body.secondary_team_id, body.player_ids
    )


@router.patch("")
def profile_patch(body: ProfilePatchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProfileService(db).update_profile(
        user,
        body.main_team_id,
        body.secondary_team_id,
        body.player_ids,
    )


@router.get("/recommendations")
def profile_recommendations(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return RecommendationService(db).get_recommendations(user)
