"""球星卡交易行 API（合规·可用积分计价）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.db.models.commerce import User
from app.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


@router.get("/browse")
def browse(
    rarity: str | None = None,
    series: str | None = None,
    list_type: str | None = None,
    sort: str = "recent",
    scope: str = "all",
    page: int = 1,
    limit: int = 24,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return MarketplaceService(db).browse(
        rarity=rarity,
        series=series,
        list_type=list_type,
        sort=sort,
        scope=scope,
        page=page,
        limit=limit,
        viewer_id=user.id,
    )


@router.get("/my-listings")
def my_listings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": MarketplaceService(db).my_listings(user)}


@router.get("/card/{card_id}/market")
def card_market(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MarketplaceService(db).card_market_data(card_id)


@router.get("/listing/{listing_id}")
def listing_detail(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MarketplaceService(db).listing_detail(listing_id, viewer_id=user.id)


class CreateListingRequest(BaseModel):
    user_card_id: int
    list_type: str = "fixed"
    price_points: int = Field(..., ge=1)
    duration_hours: int | None = None


@router.post("/list")
def create_listing(
    body: CreateListingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return MarketplaceService(db).create_listing(
        user,
        body.user_card_id,
        list_type=body.list_type,
        price_points=body.price_points,
        duration_hours=body.duration_hours,
    )


@router.post("/listing/{listing_id}/cancel")
def cancel_listing(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MarketplaceService(db).cancel_listing(user, listing_id)


@router.post("/listing/{listing_id}/buy")
def buy_now(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MarketplaceService(db).buy_now(user, listing_id)


class BidRequest(BaseModel):
    amount: int = Field(..., ge=1)


@router.post("/listing/{listing_id}/bid")
def place_bid(
    listing_id: int, body: BidRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return MarketplaceService(db).place_bid(user, listing_id, body.amount)
