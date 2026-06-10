"""010: arena battalion logs, daily rollups, user star heat, arena tier."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_arena_battalion"
down_revision: Union[str, None] = "009_news_tags_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("battalion_points_season", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("arena_tier", sa.String(20), server_default="rookie", nullable=False),
    )
    op.create_index(
        "ix_users_fav_team_battalion",
        "users",
        ["favorite_team_id", "battalion_points_season"],
    )

    op.create_table(
        "fan_activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players_detailed.id", ondelete="SET NULL"), nullable=True),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("battalion_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("star_heat_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coins_spent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ref_type", sa.String(30), nullable=True),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_fan_activity_team_created", "fan_activity_logs", ["team_id", "created_at"])
    op.create_index("ix_fan_activity_player_created", "fan_activity_logs", ["player_id", "created_at"])
    op.create_index(
        "ix_fan_activity_user_team_created",
        "fan_activity_logs",
        ["user_id", "team_id", "created_at"],
    )
    op.create_index(
        "ix_fan_activity_idempotent",
        "fan_activity_logs",
        ["user_id", "activity_type", "ref_type", "ref_id"],
        unique=True,
    )

    op.create_table(
        "team_power_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("power_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_users", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("team_id", "stat_date", name="uq_team_power_daily"),
    )

    op.create_table(
        "player_heat_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("heat_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("booster_count", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("player_id", "stat_date", name="uq_player_heat_daily"),
    )

    op.create_table(
        "team_arena_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("home_power", sa.Integer(), server_default="0", nullable=False),
        sa.Column("away_power", sa.Integer(), server_default="0", nullable=False),
        sa.Column("frozen_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("match_id", name="uq_team_arena_match"),
    )

    op.create_table(
        "user_star_heat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False),
        sa.Column("heat_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "player_id", name="uq_user_star_heat"),
    )
    op.create_index("ix_user_star_heat_player", "user_star_heat", ["player_id", "heat_total"])


def downgrade() -> None:
    op.drop_table("user_star_heat")
    op.drop_table("team_arena_snapshots")
    op.drop_table("player_heat_daily")
    op.drop_table("team_power_daily")
    op.drop_table("fan_activity_logs")
    op.drop_index("ix_users_fav_team_battalion", table_name="users")
    op.drop_column("users", "arena_tier")
    op.drop_column("users", "battalion_points_season")
