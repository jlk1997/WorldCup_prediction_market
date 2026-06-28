"""Collectible cards / digital collectibles API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.config import get_settings
from app.db.models.commerce import CollectibleCard, User, UserCollectibleCard
from app.services.collectible_chain_service import CollectibleChainService
from app.services.collectible_service import CollectibleService
from app.services.share_page_service import SharePageService

router = APIRouter(prefix="/api/collectible", tags=["collectible"])


class SynthesizeRequest(BaseModel):
    card_code: str = Field(..., min_length=2, max_length=80)
    use_coin_fill: bool = False


class UpgradeRequest(BaseModel):
    card_code: str = Field(..., min_length=2, max_length=80)
    use_coin_fill: bool = False


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
def get_card(
    card_code: str,
    user_card_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CollectibleService(db).get_card_detail(user, card_code, user_card_id=user_card_id)


@router.post("/synthesize")
def synthesize(body: SynthesizeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectibleService(db).synthesize(user, body.card_code, use_coin_fill=body.use_coin_fill)
    db.commit()
    return result


@router.post("/upgrade")
def upgrade_star(body: UpgradeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CollectibleService(db).upgrade_star(user, body.card_code, use_coin_fill=body.use_coin_fill)
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


@router.get("/user-card/{user_card_id}/chain")
def user_card_chain(
    user_card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.exceptions import NotFoundError
    from app.db.models.commerce import UserCollectibleCard

    row = db.get(UserCollectibleCard, user_card_id)
    if not row or row.user_id != user.id:
        raise NotFoundError("卡牌不存在")
    return {
        "user_card_id": row.id,
        "chain_status": row.chain_status or "none",
        "chain_nft_id": row.chain_nft_id,
        "chain_tx_hash": row.chain_tx_hash,
        "serial_no": row.serial_no,
    }


@router.post("/chain/retry/{user_card_id}")
def retry_chain_mint(
    user_card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = CollectibleChainService(db).retry_mint(user, user_card_id)
    db.commit()
    return {"chain": result}


@router.post("/chain/refresh/{user_card_id}")
def refresh_chain_mint(
    user_card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = CollectibleChainService(db).refresh_mint_status(user, user_card_id)
    return {"chain": result}


@router.get("/user-card/{user_card_id}/provenance")
def user_card_provenance(
    user_card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CollectibleService(db).get_provenance(user, user_card_id)


@router.get("/share-url")
def get_share_url(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    detail = CollectibleService(db).get_card_detail(user, code)
    svc = SharePageService(db, settings)
    url = svc.build_collectible_share_url(user.id, code)
    owned = bool(detail.get("owned"))
    star = int(detail.get("star") or 0)
    share_text = svc.build_collectible_share_text(
        nickname=user.nickname,
        card_name=detail.get("name") or code,
        rarity=detail.get("rarity") or "common",
        star=star,
        owned=owned,
        share_url=url,
    )
    chain = detail.get("chain") or {}
    return {
        "url": url,
        "share_text": share_text,
        "owned": owned,
        "card": {
            "code": detail.get("code"),
            "name": detail.get("name"),
            "rarity": detail.get("rarity"),
            "star": star,
            "image_url": detail.get("image_url"),
            "chain_minted": chain.get("status") == "minted",
            "chain_hash_short": _short_hash(chain.get("tx_hash")),
        },
    }


def _short_hash(tx_hash: str | None) -> str | None:
    if not tx_hash or len(tx_hash) < 12:
        return None
    return f"{tx_hash[:6]}…{tx_hash[-4:]}"


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
