"""一级首发打新 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db, require_admin_secret_in_production
from app.db.models.commerce import User
from app.services.collectible_service import CollectibleService
from app.services.primary_mint_service import PrimaryMintService

router = APIRouter(prefix="/api/mint-events", tags=["mint"])


@router.get("")
def list_events(user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    return {"items": PrimaryMintService(db).list_events(user)}


@router.post("/{event_id}/reserve")
def reserve(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PrimaryMintService(db).reserve(user, event_id)


@router.post("/{event_id}/purchase")
def purchase(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PrimaryMintService(db).purchase(user, event_id)


@router.post("/admin/seed-demo", dependencies=[Depends(require_admin_secret_in_production)])
def seed_demo(db: Session = Depends(get_db)):
    return PrimaryMintService(db).seed_demo_events()


@router.post("/admin/seed-collab", dependencies=[Depends(require_admin_secret_in_production)])
def seed_collab(db: Session = Depends(get_db)):
    cards = CollectibleService(db).seed_collab_cards()
    events = PrimaryMintService(db).seed_collab_events()
    return {"cards": cards, "events": events}


@router.post("/{event_id}/draw-lottery", dependencies=[Depends(require_admin_secret_in_production)])
def draw_lottery(event_id: int, db: Session = Depends(get_db)):
    return PrimaryMintService(db).draw_lottery(event_id)
