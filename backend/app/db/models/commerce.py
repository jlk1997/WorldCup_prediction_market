"""User, auth, game and commerce ORM models."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    fan_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    season_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    redeem_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_free_predict_daily: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    win_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    secondary_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fan_cheers_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fan_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    battalion_points_season: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arena_tier: Mapped[str] = mapped_column(String(20), default="rookie", nullable=False)
    has_season_pass: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    season_pass_until: Mapped[datetime | None] = mapped_column(DateTime)
    avatar_frame: Mapped[str | None] = mapped_column(String(50))
    theme_key: Mapped[str | None] = mapped_column(String(30))
    last_season_pass_daily: Mapped[date | None] = mapped_column(Date)
    last_signin_date: Mapped[date | None] = mapped_column(Date)
    signin_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referral_tier_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loss_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_cheer_tickets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_pack_live_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_pack_refresh_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)
    referred_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # 资产平台：实名认证（合规转赠/交易前置，仅存哈希，不存明文）
    real_name_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duel_elo: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    real_name_hash: Mapped[str | None] = mapped_column(String(128))
    real_name_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    favorite_team: Mapped["Team | None"] = relationship("Team", foreign_keys="User.favorite_team_id")
    referred_by: Mapped["User | None"] = relationship("User", remote_side="User.id", foreign_keys="User.referred_by_user_id")
    secondary_team: Mapped["Team | None"] = relationship("Team", foreign_keys="User.secondary_team_id")


class AuthCode(Base):
    __tablename__ = "auth_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CoinLedger(Base):
    __tablename__ = "coin_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class PointLedger(Base):
    __tablename__ = "point_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    point_bucket: Mapped[str] = mapped_column(String(10), default="season", nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class GamePrediction(Base):
    __tablename__ = "game_predictions"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_game_pred_user_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    market_type: Mapped[str] = mapped_column(String(20), default="1x2", nullable=False)
    pick: Mapped[str] = mapped_column(String(10), nullable=False)
    stake_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    redeem_points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_returned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    coins_grant: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grant_season_pass_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    product_type: Mapped[str] = mapped_column(String(30), default="coins", nullable=False)
    pay_currency: Mapped[str] = mapped_column(String(10), default="cash", nullable=False)
    redeem_price: Mapped[int | None] = mapped_column(Integer)
    grant_payload: Mapped[dict | None] = mapped_column(JSONB)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def stock_remaining(self) -> int | None:
        """None = unlimited."""
        total = self.stock_total or 0
        if total <= 0:
            return None
        return max(0, total - (self.stock_sold or 0))

    def is_out_of_stock(self) -> bool:
        total = self.stock_total or 0
        if total <= 0:
            return False
        return (self.stock_sold or 0) >= total


class RedeemOrder(Base):
    __tablename__ = "redeem_orders"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_redeem_order_idempotency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    redeem_price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship("Product")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    mint_event_id: Mapped[int | None] = mapped_column(ForeignKey("mint_events.id", ondelete="SET NULL"))
    amount_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    alipay_trade_no: Mapped[str | None] = mapped_column(String(64))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    grant_result_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship("Product")


class PaymentNotification(Base):
    __tablename__ = "payment_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    out_trade_no: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserNotification(Base):
    __tablename__ = "user_notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "ref_type", "ref_id", name="uq_user_notification_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserFavoritePlayer(Base):
    __tablename__ = "user_favorite_players"
    __table_args__ = (UniqueConstraint("user_id", "player_id", name="uq_user_fav_player"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class TeamCheer(Base):
    __tablename__ = "team_cheers"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_team_cheers_match_team"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    total_cheers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserCheer(Base):
    __tablename__ = "user_cheers"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_user_cheer_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    coins_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cheer_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class FanQuizLog(Base):
    __tablename__ = "fan_quiz_logs"
    __table_args__ = (UniqueConstraint("user_id", "quiz_date", name="uq_fan_quiz_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_date: Mapped[date] = mapped_column(Date, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class FanActivityLog(Base):
    __tablename__ = "fan_activity_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_type", "ref_type", "ref_id", name="ix_fan_activity_idempotent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players_detailed.id", ondelete="SET NULL"))
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    battalion_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    star_heat_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class TeamPowerDaily(Base):
    __tablename__ = "team_power_daily"
    __table_args__ = (UniqueConstraint("team_id", "stat_date", name="uq_team_power_daily"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    power_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PlayerHeatDaily(Base):
    __tablename__ = "player_heat_daily"
    __table_args__ = (UniqueConstraint("player_id", "stat_date", name="uq_player_heat_daily"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    heat_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    booster_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TeamArenaSnapshot(Base):
    __tablename__ = "team_arena_snapshots"
    __table_args__ = (UniqueConstraint("match_id", name="uq_team_arena_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    home_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserStarHeat(Base):
    __tablename__ = "user_star_heat"
    __table_args__ = (UniqueConstraint("user_id", "player_id", name="uq_user_star_heat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False)
    heat_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AiUsageDaily(Base):
    __tablename__ = "ai_usage_daily"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_daily"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    free_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AiAnalysisJob(Base):
    __tablename__ = "ai_analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team1: Mapped[str] = mapped_column(String(100), nullable=False)
    team2: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="pre_match", nullable=False)
    force_refresh: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    billing_json: Mapped[dict | None] = mapped_column(JSONB)
    agent_run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class ReferralBinding(Base):
    __tablename__ = "referral_bindings"
    __table_args__ = (UniqueConstraint("invitee_id", name="uq_referral_binding_invitee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invite_code_used: Mapped[str] = mapped_column(String(12), nullable=False)
    same_team_bonus_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_ip: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    inviter: Mapped["User"] = relationship("User", foreign_keys=[inviter_id])
    invitee: Mapped["User"] = relationship("User", foreign_keys=[invitee_id])


class ReferralMilestone(Base):
    __tablename__ = "referral_milestones"
    __table_args__ = (UniqueConstraint("binding_id", "milestone_key", name="uq_referral_milestone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    binding_id: Mapped[int] = mapped_column(ForeignKey("referral_bindings.id", ondelete="CASCADE"), nullable=False)
    milestone_key: Mapped[str] = mapped_column(String(30), nullable=False)
    inviter_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invitee_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inviter_battalion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invitee_battalion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inviter_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class ReferralSeasonStat(Base):
    __tablename__ = "referral_season_stats"
    __table_args__ = (UniqueConstraint("user_id", "season_key", name="uq_referral_season_stats"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_key: Mapped[str] = mapped_column(String(20), nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ReferralWeeklyAward(Base):
    __tablename__ = "referral_weekly_awards"
    __table_args__ = (UniqueConstraint("user_id", "week_key", name="uq_referral_weekly_award"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_key: Mapped[str] = mapped_column(String(12), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class LeaderboardSeasonAward(Base):
    __tablename__ = "leaderboard_season_awards"
    __table_args__ = (
        UniqueConstraint("user_id", "season_key", "board", name="uq_leaderboard_season_award"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_key: Mapped[str] = mapped_column(String(20), nullable=False)
    board: Mapped[str] = mapped_column(String(32), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    season_points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    redeem_points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class SystemUiConfig(Base):
    __tablename__ = "system_ui_configs"
    __table_args__ = (UniqueConstraint("config_key", name="uq_system_ui_config_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CollectibleCard(Base):
    __tablename__ = "collectible_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players_detailed.id", ondelete="SET NULL"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str] = mapped_column(String(20), nullable=False)
    series: Mapped[str] = mapped_column(String(40), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict | None] = mapped_column(JSONB)
    is_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime)
    available_until: Mapped[datetime | None] = mapped_column(DateTime)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserCollectibleCard(Base):
    __tablename__ = "user_collectible_cards"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False)
    star: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    highlight_json: Mapped[list | dict | None] = mapped_column(JSONB)
    obtained_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    chain_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    chain_operation_id: Mapped[str | None] = mapped_column(String(64))
    chain_class_id: Mapped[str | None] = mapped_column(String(128))
    chain_nft_id: Mapped[str | None] = mapped_column(String(128))
    chain_tx_hash: Mapped[str | None] = mapped_column(String(128))
    chain_minted_at: Mapped[datetime | None] = mapped_column(DateTime)
    chain_error: Mapped[str | None] = mapped_column(Text)
    # 资产化字段（序列号 / 流通冷却 / 锁定态 / 估值）
    serial_no: Mapped[int | None] = mapped_column(Integer)
    mint_total: Mapped[int | None] = mapped_column(Integer)
    holding_until: Mapped[datetime | None] = mapped_column(DateTime)
    tradable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lock_state: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    acquired_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    card: Mapped["CollectibleCard"] = relationship("CollectibleCard")


class UserChainAccount(Base):
    __tablename__ = "user_chain_accounts"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_chain_account_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    native_address: Mapped[str | None] = mapped_column(String(128))
    hex_address: Mapped[str | None] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(20), default="avata", nullable=False)
    chain_name: Mapped[str] = mapped_column(String(40), default="文昌链", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    operation_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CollectibleShard(Base):
    __tablename__ = "collectible_shards"
    __table_args__ = (UniqueConstraint("user_id", "rarity", name="uq_collectible_shard_user_rarity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rarity: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CardSetDefinition(Base):
    __tablename__ = "card_set_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    card_codes: Mapped[list] = mapped_column(JSONB, nullable=False)
    reward_json: Mapped[dict | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CardSetProgress(Base):
    __tablename__ = "card_set_progress"
    __table_args__ = (UniqueConstraint("user_id", "set_id", name="uq_card_set_progress_user_set"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("card_set_definitions.id", ondelete="CASCADE"), nullable=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CollectibleDropLog(Base):
    __tablename__ = "collectible_drop_logs"
    __table_args__ = (UniqueConstraint("user_id", "source", "ref_type", "ref_id", name="uq_collectible_drop_idempotent"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CollectionPassSeason(Base):
    __tablename__ = "collection_pass_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_level: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CollectionPassProgress(Base):
    __tablename__ = "collection_pass_progress"
    __table_args__ = (UniqueConstraint("user_id", "season_id", name="uq_collection_pass_progress_user_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("collection_pass_seasons.id", ondelete="CASCADE"), nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    premium_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claimed_free_json: Mapped[list | None] = mapped_column(JSONB, default=list)
    claimed_premium_json: Mapped[list | None] = mapped_column(JSONB, default=list)
    xp_boost_until: Mapped[datetime | None] = mapped_column(DateTime)
    coin_shard_fill_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coin_shard_fill_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    season: Mapped["CollectionPassSeason"] = relationship("CollectionPassSeason")


class CollectionPassXpLog(Base):
    __tablename__ = "collection_pass_xp_logs"
    __table_args__ = (UniqueConstraint("user_id", "season_id", "source", "ref_type", "ref_id", name="uq_collection_pass_xp_idempotent"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("collection_pass_seasons.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(40), nullable=False)
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CollectionQuestProgress(Base):
    __tablename__ = "collection_quest_progress"
    __table_args__ = (UniqueConstraint("user_id", "quest_key", "period_key", name="uq_collection_quest_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quest_key: Mapped[str] = mapped_column(String(40), nullable=False)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    xp_awarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CollectibleEvent(Base):
    __tablename__ = "collectible_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_series: Mapped[str] = mapped_column(String(40), default="event_limited", nullable=False)
    boost_json: Mapped[dict | None] = mapped_column(JSONB)
    coin_action_cost: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


# ======================================================================
# 足球数字资产平台（合规·积分计价二级流通 / 稀缺引擎 / 持有玩法 / 打新）
# ======================================================================


class CardSerialCounter(Base):
    """每张卡牌已发行序列号计数（用于 #N/总量 稀缺展示）。"""

    __tablename__ = "card_serial_counters"
    __table_args__ = (UniqueConstraint("card_id", name="uq_card_serial_counter_card"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False)
    issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CardTransferLog(Base):
    """卡牌流转流水：铸造/转赠/二级成交/官方回购/打新发行。计价一律为积分。"""

    __tablename__ = "card_transfer_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_card_id: Mapped[int | None] = mapped_column(Integer)
    from_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # gift/trade/buyback/mint/primary
    points_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fee_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chain_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    chain_operation_id: Mapped[str | None] = mapped_column(String(64))
    chain_tx_hash: Mapped[str | None] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), index=True)


class CardListing(Base):
    """交易行挂牌（积分计价）。一口价或英式竞拍。"""

    __tablename__ = "card_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_card_id: Mapped[int] = mapped_column(ForeignKey("user_collectible_cards.id", ondelete="CASCADE"), nullable=False)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    list_type: Mapped[str] = mapped_column(String(12), default="fixed", nullable=False)  # fixed/auction
    price_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 一口价/起拍价
    min_increment: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_bid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_bidder_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active/sold/cancelled/expired
    sold_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    sold_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    card: Mapped["CollectibleCard"] = relationship("CollectibleCard")


class MarketBid(Base):
    """竞拍出价记录（积分托管，落败自动退还）。"""

    __tablename__ = "market_bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("card_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_points: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False)  # active/outbid/won/refunded
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MarketPricePoint(Base):
    """卡牌行情成交点（积分），用于地板价/成交量/历史曲线。"""

    __tablename__ = "market_price_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    price_points: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), default="trade", nullable=False)  # trade/buyback/primary
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), index=True)


class CardStake(Base):
    """卡牌质押：锁定卡牌产被动收益 + 竞猜加成。"""

    __tablename__ = "card_stakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_card_id: Mapped[int] = mapped_column(ForeignKey("user_collectible_cards.id", ondelete="CASCADE"), nullable=False)
    card_id: Mapped[int] = mapped_column(ForeignKey("collectible_cards.id", ondelete="CASCADE"), nullable=False)
    rarity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False)  # active/released
    staked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_claim_at: Mapped[datetime | None] = mapped_column(DateTime)
    released_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_claimed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FantasyLineup(Base):
    """数字阵容：用持有球员卡组阵，按真实比赛表现周积分。"""

    __tablename__ = "fantasy_lineups"
    __table_args__ = (UniqueConstraint("user_id", "period_key", name="uq_fantasy_lineup_user_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)  # 赛季周 e.g. 2026-W23
    name: Mapped[str] = mapped_column(String(60), default="我的阵容", nullable=False)
    slots_json: Mapped[list | None] = mapped_column(JSONB, default=list)  # [user_card_id,...]
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FantasyScoreLog(Base):
    """阵容计分流水（按比赛幂等）。"""

    __tablename__ = "fantasy_score_logs"
    __table_args__ = (UniqueConstraint("lineup_id", "match_id", name="uq_fantasy_score_lineup_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lineup_id: Mapped[int] = mapped_column(ForeignKey("fantasy_lineups.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detail_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class FantasyWeeklySettlement(Base):
    """Fantasy 周榜结算发奖记录（幂等）。"""

    __tablename__ = "fantasy_weekly_settlements"
    __table_args__ = (UniqueConstraint("user_id", "period_key", name="uq_fantasy_weekly_settlement_user_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CardDuel(Base):
    """卡牌对决：异步选卡比战力。"""

    __tablename__ = "card_duels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenger_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    defender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="ai", nullable=False)  # ai/pvp
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)  # pending/settled
    challenger_card_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    defender_card_ids: Mapped[list | None] = mapped_column(JSONB)
    stake_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    challenger_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    defender_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replay_json: Mapped[dict | None] = mapped_column(JSONB)
    ai_deck_json: Mapped[list | None] = mapped_column(JSONB)
    challenger_elo_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    defender_elo_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CardDuelLog(Base):
    __tablename__ = "card_duel_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    duel_id: Mapped[int] = mapped_column(ForeignKey("card_duels.id", ondelete="CASCADE"), nullable=False, index=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    challenger_power: Mapped[int] = mapped_column(Integer, nullable=False)
    defender_power: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_side: Mapped[str] = mapped_column(String(16), nullable=False)  # challenger/defender
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CardDuelMatchQueue(Base):
    """快速匹配队列。"""

    __tablename__ = "card_duel_match_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    deck_bp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stake_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="waiting", nullable=False)  # waiting/matched/expired/cancelled
    duel_id: Mapped[int | None] = mapped_column(ForeignKey("card_duels.id", ondelete="SET NULL"), nullable=True)
    matched_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MintEvent(Base):
    """一级首发打新：限量发行，人民币或球迷币入场，支持预约/白名单/抽签。"""

    __tablename__ = "mint_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    card_code: Mapped[str] = mapped_column(String(80), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    rarity: Mapped[str] = mapped_column(String(20), default="epic", nullable=False)
    competition: Mapped[str | None] = mapped_column(String(40))
    total_supply: Mapped[int] = mapped_column(Integer, nullable=False)
    issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="coins", nullable=False)  # coins/rmb
    price_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_fen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sale_mode: Mapped[str] = mapped_column(String(16), default="public", nullable=False)  # public/whitelist/lottery
    reserve_starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)  # scheduled/reserving/live/sold_out/ended
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MintReservation(Base):
    """打新预约 / 白名单 / 抽签 / 已购记录。"""

    __tablename__ = "mint_reservations"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_mint_reservation_event_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("mint_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default="reserved", nullable=False
    )  # reserved/won/lost/claimed/payment_pending
    claimed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UserAchievement(Base):
    """资产成就解锁记录。"""

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "code", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class ProductAnalyticsEvent(Base):
    """关键产品漏斗/商业事件（运营可聚合）。"""

    __tablename__ = "product_analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    session_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
