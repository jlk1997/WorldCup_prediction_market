from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    fifa_ranking: Mapped[int | None] = mapped_column(Integer)
    group_name: Mapped[str | None] = mapped_column(String(10))
    coach: Mapped[str | None] = mapped_column(String(100))
    total_value: Mapped[str | None] = mapped_column(String(50))
    avg_age: Mapped[float | None] = mapped_column(Numeric(4, 1))
    formation: Mapped[str | None] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(Text)
    founded: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str | None] = mapped_column(String(100))
    stadium: Mapped[str | None] = mapped_column(String(100))
    capacity: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    players_detailed: Mapped[list["PlayerDetailed"]] = relationship(back_populates="team")
    players: Mapped[list["Player"]] = relationship(back_populates="team")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    jersey_number: Mapped[int | None] = mapped_column(Integer)
    is_key_player: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship(back_populates="players")


class PlayerDetailed(Base):
    __tablename__ = "players_detailed"
    __table_args__ = (Index("ix_players_detailed_team_rating", "team_id", "overall_rating"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(50))
    club: Mapped[str | None] = mapped_column(String(100))
    is_starter: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    height: Mapped[int | None] = mapped_column(Integer)
    weight: Mapped[int | None] = mapped_column(Integer)
    preferred_foot: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[str | None] = mapped_column(String(50))
    overall_rating: Mapped[int | None] = mapped_column(Integer)
    stats: Mapped[dict | None] = mapped_column(JSONB)
    honors: Mapped[list | None] = mapped_column(JSONB)
    transfers: Mapped[list | None] = mapped_column(JSONB)
    injuries: Mapped[list | None] = mapped_column(JSONB)
    injury_status: Mapped[str | None] = mapped_column(String(50))
    injury_detail: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    market_value: Mapped[str | None] = mapped_column(String(50))
    form_rating: Mapped[int | None] = mapped_column(Integer)

    team: Mapped["Team"] = relationship(back_populates="players_detailed")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str | None] = mapped_column(String(50))
    match_date: Mapped[str | None] = mapped_column(String(50))
    match_time: Mapped[str | None] = mapped_column(String(20))
    team1_name: Mapped[str | None] = mapped_column(String(100))
    team2_name: Mapped[str | None] = mapped_column(String(100))
    stadium: Mapped[str | None] = mapped_column(String(200))
    external_fixture_id: Mapped[int | None] = mapped_column(Integer)
    external_provider: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(30), default="scheduled")
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    minute: Mapped[int | None] = mapped_column(Integer)
    period: Mapped[str | None] = mapped_column(String(20))
    events_json: Mapped[list | dict | None] = mapped_column(JSONB)
    live_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    round_type: Mapped[str | None] = mapped_column(String(20), default="group")
    bracket_round: Mapped[str | None] = mapped_column(String(30))
    bracket_order: Mapped[int | None] = mapped_column(Integer)
    bracket_meta: Mapped[dict | None] = mapped_column(JSONB)


class DataSyncLog(Base):
    __tablename__ = "data_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records: Mapped[int | None] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), unique=True)
    source: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    summary: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    team_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"))
    team1: Mapped[str | None] = mapped_column(String(100))
    team2: Mapped[str | None] = mapped_column(String(100))
    mode: Mapped[str | None] = mapped_column(String(30), default="pre_match")
    steps_json: Mapped[list | None] = mapped_column(JSONB)
    final_output: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 2))
    force_refresh: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MatchPrediction(Base):
    __tablename__ = "match_predictions"
    __table_args__ = (UniqueConstraint("team1", "team2", name="uq_match_predictions_teams"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team1: Mapped[str | None] = mapped_column(String(100))
    team2: Mapped[str | None] = mapped_column(String(100))
    total_goals: Mapped[str | None] = mapped_column(String(100))
    red_cards: Mapped[str | None] = mapped_column(String(100))
    penalties: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[str | None] = mapped_column(String(100))
    advice: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


from app.db.models.commerce import (  # noqa: E402, F401
    AuthCode,
    CoinLedger,
    GamePrediction,
    Order,
    PaymentNotification,
    PointLedger,
    Product,
    RedeemOrder,
    User,
    UserBadge,
    UserSession,
)
