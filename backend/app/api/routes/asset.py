"""足球数字资产平台 API：实名、资产组合、成就、转赠、官方回购、质押、数字阵容。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db, require_admin_secret_in_production
from app.db.models.commerce import User
from app.services.card_asset_service import CardAssetService
from app.services.economy_service import EconomyService
from app.services.card_stake_service import CardStakeService
from app.services.card_transfer_service import CardTransferService
from app.services.fantasy_service import FantasyService
from app.services.realname_service import RealNameService
from app.services.asset_hub_service import AssetHubService

router = APIRouter(prefix="/api/asset", tags=["asset"])


# ----------------------- 实名认证 -----------------------
class RealNameRequest(BaseModel):
    real_name: str = Field(..., min_length=2, max_length=40)
    id_no: str = Field(..., min_length=15, max_length=18)


@router.get("/realname/status")
def realname_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return RealNameService(db).status(user)


@router.post("/realname/verify")
def realname_verify(
    body: RealNameRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    result = RealNameService(db).verify(user, body.real_name, body.id_no)
    db.commit()
    return result


# ----------------------- 资产组合 / 成就 -----------------------
@router.get("/portfolio")
def portfolio(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = CardAssetService(db)
    newly = svc.evaluate_achievements(user)
    db.commit()
    return {
        "portfolio_value": svc.portfolio_value(user.id),
        "redeem_points": user.redeem_points or 0,
        "fan_coins": user.fan_coins or 0,
        "currency_label": svc.settings.asset_currency_label,
        "newly_unlocked": newly,
        "real_name_verified": bool(user.real_name_verified),
        "disclaimer": "资产以可用积分计价，为站内虚拟收藏体验数据，无现金价值、不可提现。",
    }


@router.get("/achievements")
def achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardAssetService(db).list_achievements(user)}


@router.get("/hub-summary")
def hub_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """资产中心待办聚合：待领质押、对决、打新等徽章数据。"""
    return AssetHubService(db).hub_summary(user)


@router.get("/listing-hint")
def listing_hint(user_card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """挂牌参考价：地板价、估值与建议区间（合规积分计价）。"""
    return AssetHubService(db).listing_hint(user, user_card_id)


# ----------------------- 转赠 / 回购 -----------------------
class GiftRequest(BaseModel):
    user_card_id: int
    to_invite_code: str = Field(..., min_length=4, max_length=12)


@router.post("/gift")
def gift_card(body: GiftRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CardTransferService(db).gift(user, body.user_card_id, body.to_invite_code)


class BuybackRequest(BaseModel):
    user_card_id: int


class SplitRequest(BaseModel):
    user_card_id: int
    amount: int = Field(default=1, ge=1, le=50)


@router.post("/split")
def split_stack(body: SplitRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = CardAssetService(db).split_stack(user, body.user_card_id, amount=body.amount)
    db.commit()
    return result


@router.post("/buyback")
def buyback(body: BuybackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CardTransferService(db).buyback(user, body.user_card_id)


@router.get("/transfer-history")
def transfer_history(
    limit: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return {"items": CardTransferService(db).history(user, limit=limit)}


# ----------------------- 质押 -----------------------
class StakeRequest(BaseModel):
    user_card_id: int


@router.get("/stakes")
def list_stakes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": CardStakeService(db).list_stakes(user)}


@router.get("/battalion-boost")
def battalion_boost(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.card_battalion_service import CardBattalionService

    svc = CardBattalionService(db)
    fav_pct = svc.compute_battalion_card_boost(user, user.favorite_team_id) if user.favorite_team_id else 0
    return {
        "favorite_boost_pct": round(fav_pct * 100, 1),
        "teams": svc.summary_for_user(user),
    }


@router.post("/stake")
def stake(body: StakeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CardStakeService(db).stake(user, body.user_card_id)


@router.post("/stake/{stake_id}/claim")
def claim_stake(stake_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CardStakeService(db).claim(user, stake_id)


@router.post("/stake/{stake_id}/unstake")
def unstake(stake_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CardStakeService(db).unstake(user, stake_id)


# ----------------------- 数字阵容 -----------------------
class LineupRequest(BaseModel):
    user_card_ids: list[int]


@router.get("/fantasy")
def fantasy_lineup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FantasyService(db).fantasy_me(user)


@router.get("/fantasy/me")
def fantasy_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FantasyService(db).fantasy_me(user)


@router.get("/fantasy/score-log")
def fantasy_score_log(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": FantasyService(db).score_logs(user, limit=limit, offset=offset)}


@router.post("/fantasy")
def save_fantasy(body: LineupRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FantasyService(db).save_lineup(user, body.user_card_ids)


@router.get("/fantasy/leaderboard")
def fantasy_leaderboard(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    svc = FantasyService(db)
    payload: dict = {"items": svc.leaderboard()}
    if user:
        payload["my_rank"] = svc.user_rank(user)
        payload["reward_tiers"] = svc.reward_tiers_display()
    return payload


# ----------------------- 运营经济看板（admin） -----------------------
@router.get("/admin/economy", dependencies=[Depends(require_admin_secret_in_production)])
def economy_dashboard(days: int = 7, db: Session = Depends(get_db)):
    return EconomyService(db).dashboard(days=min(max(days, 1), 90))
