"""Collectible cards / digital collectibles API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.services.collectible_chain_service import CollectibleChainService
from app.services.collectible_service import CollectibleService

router = APIRouter(prefix="/api/collectible", tags=["collectible"])


class SynthesizeRequest(BaseModel):
    card_code: str = Field(..., min_length=2, max_length=80)


class UpgradeRequest(BaseModel):
    card_code: str = Field(..., min_length=2, max_length=80)


@router.get("/summary")
def get_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CollectibleService(db).get_summary(user)


@router.get("/activity")
def get_activity(
    limit: int = 15,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = CollectibleService(db).get_recent_activity(user, limit=min(max(limit, 1), 50))
    return {"items": items}


@router.get("/costs")
def get_costs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CollectibleService(db).get_cost_tables()


@router.get("/album")
def get_album(
    rarity: str | None = None,
    series: str | None = None,
    owned_only: bool = False,
    page: int = 1,
    limit: int = 60,
    brief: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CollectibleService(db).get_album(
        user,
        rarity=rarity,
        series=series,
        owned_only=owned_only,
        page=page,
        limit=limit,
        brief=brief,
    )


@router.get("/owned-preview")
def owned_preview(
    limit: int = 6,
    min_rarity: str = "rare",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cards = CollectibleService(db).get_owned_preview(user, limit=limit, min_rarity=min_rarity)
    return {"cards": cards}


@router.get("/sets")
def get_sets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"sets": CollectibleService(db).get_sets(user)}


@router.get("/synthesis-options")
def synthesis_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"options": CollectibleService(db).synthesis_options(user)}


@router.get("/card/{card_code}")
def get_card(card_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CollectibleService(db).get_card_detail(user, card_code)


@router.post("/synthesize")
def synthesize(body: SynthesizeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectibleService(db).synthesize(user, body.card_code)
    db.commit()
    return result


@router.post("/upgrade")
def upgrade_star(body: UpgradeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectibleService(db).upgrade_star(user, body.card_code)
    db.commit()
    return result


@router.post("/sets/{set_code}/claim")
def claim_set(set_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectibleService(db).claim_set_reward(user, set_code)
    db.commit()
    return result


@router.get("/chain/status")
def chain_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CollectibleService(db).get_chain_status(user)


@router.post("/chain/retry/{user_card_id}")
def retry_chain_mint(
    user_card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = CollectibleChainService(db).retry_mint(user, user_card_id)
    db.commit()
    return {"chain": result}


@router.get("/metadata/{user_card_id}.json")
def nft_metadata(user_card_id: int, db: Session = Depends(get_db)):
    row = db.get(UserCollectibleCard, user_card_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    card = db.get(CollectibleCard, row.card_id)
    user = db.get(User, row.user_id)
    if not card or not user:
        raise HTTPException(status_code=404, detail="not found")
    return CollectibleChainService(db).build_metadata(row, card, user)
