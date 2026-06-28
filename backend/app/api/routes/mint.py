"""一级首发打新 API。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db, require_admin_secret_in_production
from app.api.schemas.commerce import (
    CreatePayResponse,
    MintCreateOrderRequest,
    MintEventAdminCreate,
    MintEventAdminUpdate,
    OrderOut,
)
from app.core.exceptions import BadRequestError
from app.core.rate_limit import rate_limit_pay
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


@router.get("/{event_id}/advisor")
def mint_advisor(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.agent_asset_context import AgentAssetContextService

    return AgentAssetContextService(db).mint_advisor(user, event_id)


@router.post("/{event_id}/create-order", response_model=CreatePayResponse)
def create_rmb_order(
    event_id: int,
    body: MintCreateOrderRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.age_confirmed:
        raise BadRequestError("请先确认已满 18 周岁并知悉虚拟商品规则")
    from app.services.anti_cheat_service import AntiCheatService

    AntiCheatService().check_mint_order(request, user.id)
    rate_limit_pay(user.id)
    order, pay_url, channel = PrimaryMintService(db).create_rmb_order(
        user,
        event_id,
        pay_channel=body.pay_channel,
        user_agent=request.headers.get("user-agent"),
    )
    return CreatePayResponse(
        order=OrderOut.model_validate(order),
        pay_url=pay_url,
        pay_channel=channel,
    )


@router.post("/admin/seed-demo", dependencies=[Depends(require_admin_secret_in_production)])
def seed_demo(db: Session = Depends(get_db)):
    return PrimaryMintService(db).seed_demo_events()


@router.get("/admin/events", dependencies=[Depends(require_admin_secret_in_production)])
def admin_list_events(db: Session = Depends(get_db)):
    return {"items": PrimaryMintService(db).admin_list_events()}


@router.post("/admin/events", dependencies=[Depends(require_admin_secret_in_production)])
def admin_create_event(body: MintEventAdminCreate, db: Session = Depends(get_db)):
    return PrimaryMintService(db).admin_create_event(body.model_dump())


@router.patch("/admin/events/{event_id}", dependencies=[Depends(require_admin_secret_in_production)])
def admin_update_event(
    event_id: int, body: MintEventAdminUpdate, db: Session = Depends(get_db)
):
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    return PrimaryMintService(db).admin_update_event(event_id, payload)


@router.post("/admin/seed-collab", dependencies=[Depends(require_admin_secret_in_production)])
def seed_collab(db: Session = Depends(get_db)):
    cards = CollectibleService(db).seed_collab_cards()
    events = PrimaryMintService(db).seed_collab_events()
    return {"cards": cards, "events": events}


@router.post("/{event_id}/draw-lottery", dependencies=[Depends(require_admin_secret_in_production)])
def draw_lottery(event_id: int, db: Session = Depends(get_db)):
    return PrimaryMintService(db).draw_lottery(event_id)
