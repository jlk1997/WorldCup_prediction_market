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
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)
    referred_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
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
    amount_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    alipay_trade_no: Mapped[str | None] = mapped_column(String(64))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
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
    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_user_collectible_card"),)

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
