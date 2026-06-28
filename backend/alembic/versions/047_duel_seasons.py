"""Duel ranked seasons + match queue mode."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "047_duel_seasons"
down_revision = "046_season_ultimate_matchday"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "duel_seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("reward_json", JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_duel_seasons_status", "duel_seasons", ["status"])

    op.create_table(
        "duel_season_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("duel_seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("elo", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("games", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tier", sa.String(32), server_default="bronze", nullable=False),
        sa.Column("reward_claimed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "season_id", name="uq_duel_season_stats_user_season"),
    )
    op.create_index("ix_duel_season_stats_season_elo", "duel_season_stats", ["season_id", "elo"])

    op.add_column(
        "card_duel_match_queue",
        sa.Column("match_mode", sa.String(16), server_default="casual", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("card_duel_match_queue", "match_mode")
    op.drop_index("ix_duel_season_stats_season_elo", table_name="duel_season_stats")
    op.drop_table("duel_season_stats")
    op.drop_index("ix_duel_seasons_status", table_name="duel_seasons")
    op.drop_table("duel_seasons")
