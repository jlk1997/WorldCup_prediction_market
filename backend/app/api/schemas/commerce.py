from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendCodeRequest(BaseModel):
    email: EmailStr
    age_confirmed: bool = Field(description="用户确认已满18周岁并同意协议")


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)
    age_confirmed: bool = Field(description="用户确认已满18周岁并同意协议")
    invite_code: str | None = Field(default=None, max_length=12)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nickname: str
    avatar_url: str | None = None
    avatar_frame: str | None = None
    theme_key: str | None = None
    fan_coins: int
    season_points: int
    redeem_points: int = 0
    extra_free_predict_daily: int = 0
    win_streak: int
    level: int
    favorite_team_id: int | None = None
    secondary_team_id: int | None = None
    profile_completed: bool = False
    fan_cheers_total: int = 0
    fan_level: int = 1
    battalion_points_season: int = 0
    arena_tier: str = "rookie"
    has_season_pass: bool
    has_active_season_pass: bool = False
    season_pass_until: datetime | None = None
    last_signin_date: date | None = None
    signin_streak: int = 0


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
    is_new: bool = False
    referral: dict | None = None


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=100)
    favorite_team_id: int | None = None


class PredictSubmitRequest(BaseModel):
    match_id: int
    pick: str
    stake_coins: int = 0
    use_free: bool = False


class PredictRaiseStakeRequest(BaseModel):
    match_id: int
    additional_stake_coins: int = Field(ge=1, description="追加质押球迷币数量")


class GamePredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    pick: str
    stake_coins: int
    is_free: bool
    status: str
    points_awarded: int
    redeem_points_awarded: int = 0
    coins_returned: int
    pick_label: str | None = None
    status_label: str | None = None
    team1: str | None = None
    team2: str | None = None
    match_date: str | None = None
    match_time: str | None = None
    final_score: str | None = None
    settled_at: datetime | None = None
    created_at: datetime | None = None


class GameMatchCardOut(BaseModel):
    id: int
    group: str | None = None
    date: str | None = None
    time: str | None = None
    team1: str | None = None
    team2: str | None = None
    stadium: str | None = None
    user_predicted: bool = False
    user_pick: str | None = None
    user_prediction_status: str | None = None
    user_stake_coins: int | None = None
    user_is_free: bool = False


class UserNotificationOut(BaseModel):
    id: int
    category: str
    title: str
    body: str
    payload: dict | None = None
    read_at: datetime | None = None
    created_at: datetime | None = None


class MarkNotificationsReadRequest(BaseModel):
    ids: list[int] | None = None


class LeaderboardRowOut(BaseModel):
    rank: int | None = None
    user_id: int
    nickname: str
    points: int | None = None
    season_points: int | None = None
    redeem_points: int | None = None
    battalion_points: int | None = None
    win_streak: int = 0
    win_rate: float | None = None
    wins: int | None = None
    settled: int | None = None
    predict_points: int | None = None
    arena_tier: str | None = None
    tier_label: str | None = None
    is_me: bool = False


class LeaderboardBoardOut(BaseModel):
    board: str
    period: str
    period_label: str
    metric: str
    description: str
    min_samples: int | None = None
    rows: list[LeaderboardRowOut]


class MyLeaderboardSummaryOut(BaseModel):
    user_id: int
    nickname: str
    season_points: int
    season_rank: int | None = None
    season_gap_to_prev: int | None = None
    redeem_points: int = 0
    redeem_rank: int | None = None
    redeem_gap_to_prev: int | None = None
    daily_points: int
    daily_rank: int | None = None
    redeem_daily_points: int = 0
    redeem_daily_rank: int | None = None
    weekly_points: int
    weekly_rank: int | None = None
    redeem_weekly_points: int = 0
    redeem_weekly_rank: int | None = None
    win_streak: int
    battalion_points: int
    battalion_rank: int | None = None
    battalion_team: str | None = None
    arena_tier: str
    tier_label: str
    predict: dict
    predict_accuracy_rank: int | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price_fen: int
    coins_grant: int
    grant_season_pass_days: int
    product_type: str
    pay_currency: str = "cash"
    redeem_price: int | None = None
    grant_payload: dict | None = None
    per_user_limit: int = 0
    stock_total: int = 0
    stock_sold: int = 0
    featured: bool = False


class RedeemProductOut(ProductOut):
    user_purchased_count: int = 0
    stock_remaining: int | None = None
    is_unlimited_stock: bool = True
    is_out_of_stock: bool = False
    can_purchase: bool = False
    purchase_blocked_reason: str | None = None


class RedeemPurchaseRequest(BaseModel):
    product_id: int
    idempotency_key: str | None = Field(default=None, max_length=64)


class RedeemOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    redeem_price: int
    status: str
    created_at: datetime | None = None
    product_name: str | None = None


class RedeemPurchaseOut(BaseModel):
    order: RedeemOrderOut
    redeem_points_after: int
    stock_remaining: int | None = None


class RedeemProductAdminCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    redeem_price: int = Field(gt=0)
    grant_payload: dict
    per_user_limit: int = Field(default=0, ge=0)
    stock_total: int = Field(default=0, ge=0)
    sort_order: int = 0
    featured: bool = False
    active: bool = True


class RedeemProductAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    redeem_price: int | None = Field(default=None, gt=0)
    grant_payload: dict | None = None
    per_user_limit: int | None = Field(default=None, ge=0)
    stock_total: int | None = Field(default=None, ge=0)
    sort_order: int | None = None
    featured: bool | None = None
    active: bool | None = None


class RedeemProductAdminOut(ProductOut):
    active: bool
    stock_remaining: int | None = None
    updated_at: datetime | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    out_trade_no: str
    amount_fen: int
    status: str
    paid_at: datetime | None = None


class OrderDetailOut(OrderOut):
    product_name: str
    product_type: str
    coins_grant: int
    grant_season_pass_days: int
    alipay_trade_no: str | None = None
    grant_summary: list[str] = Field(default_factory=list)


class CreateOrderRequest(BaseModel):
    product_id: int
    age_confirmed: bool = Field(description="用户确认已满18周岁并知悉虚拟商品规则")
    pay_channel: Literal["auto", "page", "wap"] = "auto"


class CreatePayResponse(BaseModel):
    order: OrderOut
    pay_url: str
    pay_channel: Literal["page", "wap"]
