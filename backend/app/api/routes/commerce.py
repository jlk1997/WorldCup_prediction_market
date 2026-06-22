from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db, require_admin_secret_in_production, require_manual_sync
from app.api.schemas.profile import CheerSubmitRequest, QuizAnswerRequest
from app.api.schemas.commerce import (
    AuthTokenResponse,
    CreateOrderRequest,
    CreatePayResponse,
    GamePredictionOut,
    OrderDetailOut,
    OrderOut,
    PredictRaiseStakeRequest,
    PredictSubmitRequest,
    PredictSubmitResponse,
    ProductOut,
    RedeemProductOut,
    RedeemProductAdminCreate,
    RedeemProductAdminOut,
    RedeemProductAdminUpdate,
    RedeemOrderOut,
    RedeemPurchaseOut,
    RedeemPurchaseRequest,
    RefreshTokenRequest,
    SendCodeRequest,
    UpdateProfileRequest,
    UserNotificationOut,
    PredictRevealConfigOut,
    PredictRevealConfigUpdate,
    UserOut,
    VerifyCodeRequest,
    MarkNotificationsReadRequest,
    MyLeaderboardSummaryOut,
    LeaderboardBoardOut,
)
from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.core.rate_limit import (
    client_ip,
    rate_limit_arena_spend,
    rate_limit_pay,
    rate_limit_pay_sync,
    rate_limit_redeem,
    rate_limit_refresh,
)
from app.db.models.commerce import Product, User
from app.services.arena_service import ArenaService
from app.services.auth_service import AuthService
from app.services.game_service import GameService
from app.services.leaderboard_service import LeaderboardService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.db.repositories.user_repository import UserRepository, WalletRepository
from app.services.referral_service import ReferralService
from app.services.season_pass_service import SeasonPassService

router_auth = APIRouter(prefix="/api/auth", tags=["auth"])
router_game = APIRouter(prefix="/api/game", tags=["game"])
router_shop = APIRouter(prefix="/api/shop", tags=["shop"])
router_pay = APIRouter(prefix="/api/pay", tags=["pay"])
router_wallet = APIRouter(prefix="/api/wallet", tags=["wallet"])


def _user_out(user: User) -> UserOut:
    from app.services.entitlements import has_active_season_pass

    data = UserOut.model_validate(user).model_dump()
    data["has_active_season_pass"] = has_active_season_pass(user)
    return UserOut(**data)


@router_auth.post("/send-code")
def send_code(body: SendCodeRequest, request: Request, db: Session = Depends(get_db)):
    AuthService(db).send_code(body.email, client_ip(request), body.age_confirmed)
    return {"status": "ok", "message": "验证码已发送，请查收邮件"}


@router_auth.post("/verify", response_model=AuthTokenResponse)
def verify_code(body: VerifyCodeRequest, request: Request, db: Session = Depends(get_db)):
    user, access, refresh, is_new, bind_failure = AuthService(db).verify_and_login(
        body.email, body.code, body.age_confirmed, client_ip(request), body.invite_code
    )
    db.refresh(user)
    referral = ReferralService(db).login_referral_info(
        user,
        is_new=is_new,
        invite_code_attempted=body.invite_code,
        bind_failure=bind_failure,
    )
    return AuthTokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=_user_out(user),
        is_new=is_new,
        referral=referral,
    )


@router_auth.post("/refresh", response_model=dict)
def refresh_token(body: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit_refresh(request, body.refresh_token)
    access, refresh, user_id = AuthService(db).refresh_tokens(body.refresh_token)
    user = UserRepository(db).get_by_id(user_id)
    if user:
        SeasonPassService(db).grant_daily_if_eligible(user)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router_auth.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    SeasonPassService(db).grant_daily_if_eligible(user)
    refreshed = UserRepository(db).get_by_id(user.id)
    return _user_out(refreshed or user)


@router_wallet.get("/ledger")
def coin_ledger(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
):
    rows = WalletRepository(db).list_coin_ledger(user.id, limit)
    return {"status": "success", "data": rows}


@router_wallet.get("/point-ledger")
def point_ledger(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bucket: str = Query("season", pattern="^(season|redeem)$"),
    limit: int = Query(50, ge=1, le=100),
):
    rows = WalletRepository(db).list_point_ledger(user.id, bucket=bucket, limit=limit)
    return {"status": "success", "bucket": bucket, "data": rows}


@router_auth.patch("/me", response_model=UserOut)
def update_me(body: UpdateProfileRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = UserRepository(db)
    updated = user
    if body.nickname is not None and body.nickname.strip() and body.nickname.strip() != user.nickname:
        updated = repo.change_nickname(user, body.nickname.strip())
    if body.favorite_team_id is not None:
        updated = repo.update_profile(updated, favorite_team_id=body.favorite_team_id)
    return _user_out(updated)


@router_game.get("/matches")
def game_matches(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return GameService(db).list_predictable_match_cards(user)


@router_game.post("/predict", response_model=PredictSubmitResponse)
def submit_predict(
    body: PredictSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pred = GameService(db).submit_prediction(
        user, body.match_id, body.pick, body.stake_coins, body.use_free
    )
    bonus = getattr(pred, "_arena_combo_battalion", 0)
    return PredictSubmitResponse(
        prediction=GamePredictionOut.model_validate(pred),
        arena_battalion_bonus=bonus,
    )


@router_game.post("/predict/raise-stake", response_model=GamePredictionOut)
def raise_predict_stake(
    body: PredictRaiseStakeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pred = GameService(db).raise_prediction_stake(
        user, body.match_id, body.additional_stake_coins
    )
    return GamePredictionOut.model_validate(pred)


@router_game.get("/my-predictions", response_model=list[GamePredictionOut])
def my_predictions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [GamePredictionOut.model_validate(p) for p in GameService(db).my_predictions(user.id)]


@router_game.get("/pending-predictions-count")
def pending_predictions_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = GameService(db).pending_predictions_count(user.id)
    return {"count": count}


@router_game.get("/notifications", response_model=list[UserNotificationOut])
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = Query(False),
    category: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    try:
        from app.core.predict_notify_parse import enrich_predict_payload

        rows = NotificationService(db).list_for_user(
            user.id, unread_only=unread_only, category=category, limit=limit
        )
        out: list[UserNotificationOut] = []
        for row in rows:
            item = UserNotificationOut.model_validate(row)
            if item.category == NotificationService.CATEGORY_PREDICT:
                enriched = enrich_predict_payload(item.payload, item.body)
                item = item.model_copy(update={"payload": enriched})
            out.append(item)
        return out
    except SQLAlchemyError:
        raise ServiceUnavailableError("通知暂不可用，请确认已执行数据库迁移") from None


@router_game.get("/predict-reveal-config", response_model=PredictRevealConfigOut)
def get_predict_reveal_config(db: Session = Depends(get_db)):
    from app.services.predict_reveal_config_service import PredictRevealConfigService

    cfg = PredictRevealConfigService(db).get_config()
    return PredictRevealConfigOut.model_validate(cfg)


@router_game.put("/admin/predict-reveal-config", response_model=PredictRevealConfigOut)
def update_predict_reveal_config(
    body: PredictRevealConfigUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.predict_reveal_config_service import PredictRevealConfigService

    patch = body.model_dump(exclude_unset=True)
    cfg = PredictRevealConfigService(db).upsert_config(patch)
    db.commit()
    return PredictRevealConfigOut.model_validate(cfg)


@router_game.get("/notifications/unread-count")
def notifications_unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = Query(None),
):
    try:
        count = NotificationService(db).unread_count(user.id, category=category)
        return {"count": count}
    except SQLAlchemyError:
        return {"count": 0}


@router_game.get("/notifications/badge")
def notifications_badge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        counts = NotificationService(db).unread_badge(user.id)
        return {"counts": counts, "total": sum(counts.values())}
    except SQLAlchemyError:
        return {"counts": {}, "total": 0}


@router_game.post("/notifications/read")
def mark_notifications_read(
    body: MarkNotificationsReadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = NotificationService(db).mark_read(user.id, body.ids)
    db.commit()
    return {"updated": updated}


@router_game.post("/admin/settle", dependencies=[Depends(require_manual_sync)])
def admin_settle_predictions(db: Session = Depends(get_db)):
    return GameService(db).settle_all_pending()


@router_game.post("/signin")
def signin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return GameService(db).signin(user)


@router_game.post("/qq-group/claim")
def claim_qq_group_reward(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = GameService(db).claim_qq_group_reward(user)
    db.commit()
    db.refresh(user)
    result["fan_coins"] = user.fan_coins
    return result


@router_game.get("/daily-status")
def daily_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return GameService(db).get_daily_status(user)


@router_game.post("/season-pass/daily-claim")
def claim_season_pass_daily(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = SeasonPassService(db).grant_daily_if_eligible(user, commit=False)
    if result.get("granted", 0) > 0:
        db.commit()
        refreshed = UserRepository(db).get_by_id(user.id)
        if refreshed:
            result["fan_coins"] = refreshed.fan_coins
    else:
        db.rollback()
    return result


@router_game.get("/admin/funnel-summary", dependencies=[Depends(require_admin_secret_in_production)])
def funnel_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    from app.services.funnel_service import FunnelService

    return FunnelService(db).summary(days)


@router_game.get("/leaderboard/reward-tiers")
def leaderboard_reward_tiers(db: Session = Depends(get_db)):
    return LeaderboardService(db).get_reward_tiers()


@router_game.post("/admin/leaderboard/settle-season", dependencies=[Depends(require_admin_secret_in_production)])
def admin_settle_season_leaderboard(
    board: str = Query("points"),
    season_key: str | None = Query(None),
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    result = LeaderboardService(db).settle_season_board(
        board=board,
        season_key=season_key,
        force=force,
    )
    return result


@router_game.get("/matches/{match_id}/pick-stats")
def match_pick_stats(match_id: int, db: Session = Depends(get_db)):
    return GameService(db).get_match_pick_stats(match_id)


@router_game.get("/predict/preview")
def predict_preview(
    pick: str = Query(...),
    stake_coins: int = Query(0, ge=0),
    use_free: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GameService(db).preview_predict(user, pick, stake_coins, use_free)


@router_game.get("/win-feed")
def win_feed(limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    return GameService(db).get_win_feed(limit)


@router_game.get("/leaderboard")
def leaderboard(
    period: str = Query("season"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    svc = LeaderboardService(db)
    if period in ("daily", "weekly", "season"):
        return svc.legacy_points_list(period)
    return svc.legacy_points_list("season")


@router_game.get("/leaderboard/board", response_model=LeaderboardBoardOut)
def leaderboard_board(
    board: str = Query("points"),
    period: str = Query("season"),
    team_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    svc = LeaderboardService(db)
    viewer = user.id if user else None
    if board == "predict_accuracy":
        data = svc.get_predict_accuracy_board(limit=limit, viewer_id=viewer)
    elif board == "redeem_points":
        data = svc.get_redeem_points_board(period, limit, viewer)
    elif board == "battalion":
        rows_raw = ArenaService(db).get_team_battalion_leaderboard(team_id, period, limit)
        from app.services.leaderboard_service import BOARD_RULES, PERIOD_LABELS

        rows = []
        for idx, r in enumerate(rows_raw):
            rows.append(
                {
                    **r,
                    "rank": idx + 1,
                    "points": r["battalion_points"],
                    "is_me": viewer is not None and r["user_id"] == viewer,
                }
            )
        p = period if period in PERIOD_LABELS else "season"
        data = {
            "board": "battalion",
            "period": p,
            "period_label": PERIOD_LABELS.get(p, p),
            "metric": "battalion_points",
            "description": BOARD_RULES["battalion"].get(p, BOARD_RULES["battalion"]["season"]),
            "rows": rows,
        }
    elif board == "supporter":
        if not team_id:
            raise HTTPException(status_code=400, detail="应援榜需指定 team_id")
        rows_raw = ArenaService(db).get_team_supporter_leaderboard(team_id, period, limit)
        from app.services.leaderboard_service import BOARD_RULES, PERIOD_LABELS

        rows = []
        for idx, r in enumerate(rows_raw):
            rows.append(
                {
                    **r,
                    "rank": idx + 1,
                    "points": r["battalion_points"],
                    "is_me": viewer is not None and r["user_id"] == viewer,
                }
            )
        p = period if period in PERIOD_LABELS else "season"
        data = {
            "board": "supporter",
            "period": p,
            "period_label": PERIOD_LABELS.get(p, p),
            "metric": "battalion_points",
            "description": BOARD_RULES["supporter"].get(p, BOARD_RULES["supporter"]["season"]),
            "rows": rows,
        }
    else:
        data = svc.get_points_board(period, limit, viewer)
    return LeaderboardBoardOut.model_validate(data)


@router_game.get("/leaderboard/me", response_model=MyLeaderboardSummaryOut)
def leaderboard_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MyLeaderboardSummaryOut.model_validate(LeaderboardService(db).get_my_summary(user))


@router_game.get("/leaderboard/rules")
def leaderboard_rules(db: Session = Depends(get_db)):
    return LeaderboardService(db).get_rules()


@router_game.get("/fan-rank")
def fan_rank(db: Session = Depends(get_db)):
    return GameService(db).fan_rank()


@router_game.get("/team-contribution")
def team_contribution(team_id: int | None = Query(None), db: Session = Depends(get_db)):
    return GameService(db).team_contribution_leaderboard(team_id=team_id)


@router_game.get("/cheer/{match_id}")
def cheer_status(
    match_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return GameService(db).get_cheer_status(match_id, user.id if user else None)


@router_game.post("/cheer")
def submit_cheer(body: CheerSubmitRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit_arena_spend(user.id)
    return GameService(db).submit_cheer(user, body.match_id, body.team_id)


@router_game.get("/quiz/today")
def quiz_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return GameService(db).get_quiz_today(user)


@router_game.post("/quiz/answer")
def quiz_answer(body: QuizAnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return GameService(db).answer_quiz(user, body.answer_index)


@router_game.get("/fan-card")
def fan_card(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return GameService(db).get_fan_card(user)


@router_game.get("/share/card-url")
def fan_card_share_url(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.core.config import get_settings
    from app.services.share_page_service import SharePageService

    settings = get_settings()
    svc = SharePageService(db, settings)
    return {"share_url": svc.build_card_share_url(user)}


@router_game.get("/share/predict/{prediction_id}")
def predict_share_url(
    prediction_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.config import get_settings
    from app.db.models.commerce import GamePrediction
    from app.services.share_page_service import SharePageService

    pred = db.get(GamePrediction, prediction_id)
    if not pred or pred.user_id != user.id:
        raise HTTPException(status_code=404, detail="prediction_not_found")
    if pred.status != "won":
        raise HTTPException(status_code=400, detail="prediction_not_won")
    settings = get_settings()
    svc = SharePageService(db, settings)
    return {"share_url": svc.build_predict_share_url(prediction_id)}


@router_shop.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return [ProductOut.model_validate(p) for p in PaymentService(db).list_products()]


@router_shop.get("/redeem/products", response_model=list[RedeemProductOut])
def list_redeem_products(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    from app.services.redeem_shop_service import RedeemShopService

    svc = RedeemShopService(db)
    rows = svc.list_products_enriched(user)
    out: list[RedeemProductOut] = []
    for row in rows:
        base = ProductOut.model_validate(row["product"]).model_dump()
        out.append(
            RedeemProductOut(
                **base,
                user_purchased_count=row["user_purchased_count"],
                stock_remaining=row["stock_remaining"],
                is_unlimited_stock=row["is_unlimited_stock"],
                is_out_of_stock=row["is_out_of_stock"],
                can_purchase=row["can_purchase"],
                purchase_blocked_reason=row["purchase_blocked_reason"],
            )
        )
    return out


@router_shop.post("/redeem/purchase", response_model=RedeemPurchaseOut)
def redeem_purchase(
    body: RedeemPurchaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.redeem_shop_service import RedeemShopService

    rate_limit_redeem(user.id)
    result = RedeemShopService(db).purchase(
        user.id, body.product_id, idempotency_key=body.idempotency_key
    )
    order = result["order"]
    product = db.get(Product, order.product_id)
    order_out = RedeemOrderOut.model_validate(order).model_copy(
        update={"product_name": product.name if product else None}
    )
    return RedeemPurchaseOut(
        order=order_out,
        redeem_points_after=result["redeem_points_after"],
        stock_remaining=result.get("stock_remaining"),
    )


@router_shop.get("/redeem/orders", response_model=list[RedeemOrderOut])
def list_redeem_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.redeem_shop_service import RedeemShopService

    rows = RedeemShopService(db).list_user_orders(user.id)
    return [RedeemOrderOut.model_validate(r) for r in rows]


@router_shop.get("/redeem/rules")
def redeem_shop_rules(db: Session = Depends(get_db)):
    from app.core.config import get_settings
    from app.services.product_catalog_service import ProductCatalogService
    from app.services.redeem_shop_service import RedeemShopService

    settings = get_settings()
    ratio = settings.predict_win_redeem_ratio
    catalog_docs = ProductCatalogService(db).catalog_docs()
    items = [
        {
            "sku": p.sku,
            "name": p.name,
            "redeem_price": p.redeem_price,
            "per_user_limit": p.per_user_limit,
            "stock_total": p.stock_total,
            "stock_sold": p.stock_sold,
            "stock_remaining": p.stock_remaining(),
            "grant_payload": p.grant_payload,
        }
        for p in RedeemShopService(db).list_products()
    ]
    return {
        "economy": {
            "season_points_label": "累计积分",
            "redeem_points_label": "可用积分",
            "season_points_desc": "猜中、召友荣誉等活跃成就获得，用于累计积分榜排名；兑换与回购不扣减、也不增加。",
            "redeem_points_desc": "竞猜猜中、卡牌回购/交易、套组奖励、质押产出等获得，用于积分兑换商城与卡牌流通。",
            "predict_win_redeem_ratio": ratio,
            "no_loss_reward": True,
        },
        "products": items,
        **catalog_docs,
    }


def _admin_product_out(p) -> RedeemProductAdminOut:
    base = ProductOut.model_validate(p).model_dump()
    return RedeemProductAdminOut(
        **base,
        active=p.active,
        stock_remaining=p.stock_remaining(),
        updated_at=p.updated_at,
    )


@router_shop.get("/admin/redeem/products", response_model=list[RedeemProductAdminOut])
def admin_list_redeem_products(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_product_admin_service import RedeemProductAdminService

    return [_admin_product_out(p) for p in RedeemProductAdminService(db).list_all()]


@router_shop.get("/admin/redeem/products/{product_id}", response_model=RedeemProductAdminOut)
def admin_get_redeem_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_product_admin_service import RedeemProductAdminService

    return _admin_product_out(RedeemProductAdminService(db).get(product_id))


@router_shop.post("/admin/redeem/products", response_model=RedeemProductAdminOut)
def admin_create_redeem_product(
    body: RedeemProductAdminCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_product_admin_service import RedeemProductAdminService

    product = RedeemProductAdminService(db).create(
        sku=body.sku,
        name=body.name,
        description=body.description,
        redeem_price=body.redeem_price,
        grant_payload=body.grant_payload,
        per_user_limit=body.per_user_limit,
        stock_total=body.stock_total,
        sort_order=body.sort_order,
        featured=body.featured,
        active=body.active,
    )
    return _admin_product_out(product)


@router_shop.patch("/admin/redeem/products/{product_id}", response_model=RedeemProductAdminOut)
def admin_update_redeem_product(
    product_id: int,
    body: RedeemProductAdminUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_product_admin_service import RedeemProductAdminService

    fields = body.model_dump(exclude_unset=True)
    grant_payload = fields.pop("grant_payload", None)
    grant_payload_set = "grant_payload" in body.model_dump(exclude_unset=True)
    product = RedeemProductAdminService(db).update(
        product_id,
        grant_payload_set=grant_payload_set,
        grant_payload=grant_payload,
        **fields,
    )
    return _admin_product_out(product)


@router_shop.post("/admin/redeem/products/{product_id}/toggle", response_model=RedeemProductAdminOut)
def admin_toggle_redeem_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_product_admin_service import RedeemProductAdminService

    return _admin_product_out(RedeemProductAdminService(db).toggle_active(product_id))


@router_shop.post("/admin/sync-catalog")
def admin_sync_redeem_catalog(
    deactivate_missing: bool = Query(False),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    """Deprecated: bootstrap only. Daily ops use /admin/redeem/products."""
    from app.services.product_catalog_service import ProductCatalogService

    return ProductCatalogService(db).sync_redeem_catalog(deactivate_missing=deactivate_missing)


@router_shop.post("/admin/redeem/refund")
def admin_refund_redeem_order(
    order_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    from app.services.redeem_shop_service import RedeemShopService

    return RedeemShopService(db).admin_refund_order(order_id)


@router_pay.post("/alipay/create", response_model=CreatePayResponse)
def create_alipay_order(
    body: CreateOrderRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.age_confirmed:
        raise BadRequestError("请先确认已满 18 周岁并知悉虚拟商品规则")
    rate_limit_pay(user.id)
    order, pay_url, channel = PaymentService(db).create_order(
        user.id,
        body.product_id,
        pay_channel=body.pay_channel,
        user_agent=request.headers.get("user-agent"),
    )
    return CreatePayResponse(
        order=OrderOut.model_validate(order),
        pay_url=pay_url,
        pay_channel=channel,
    )


@router_pay.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = dict(form)
    result = PaymentService(db).handle_notify(data)
    return result


@router_pay.post("/alipay/sync", response_model=OrderDetailOut)
def sync_alipay_order(
    out_trade_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """When async notify failed, query Alipay and fulfill if already paid."""
    rate_limit_pay_sync(user.id)
    svc = PaymentService(db)
    order = svc.sync_order_from_alipay(out_trade_no, user.id)
    return OrderDetailOut.model_validate(svc.order_detail(order))


@router_pay.post("/alipay/mock-pay", response_model=OrderDetailOut)
def mock_pay(
    out_trade_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = PaymentService(db)
    order = svc.mock_pay_success(out_trade_no, user.id)
    return OrderDetailOut.model_validate(svc.order_detail(order))


@router_pay.get("/orders", response_model=list[OrderOut])
def list_my_orders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    orders = PaymentService(db).list_user_orders(user.id, limit)
    return [OrderOut.model_validate(o) for o in orders]


@router_pay.get("/orders/by-no/{out_trade_no}", response_model=OrderDetailOut)
def get_order_by_trade_no(
    out_trade_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = PaymentService(db)
    order = svc.get_order_by_trade_no(out_trade_no, user.id)
    return OrderDetailOut.model_validate(svc.order_detail(order))


@router_pay.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = PaymentService(db).get_order(order_id, user.id)
    return OrderOut.model_validate(order)
