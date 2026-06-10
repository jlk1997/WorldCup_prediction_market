"""007: fan profile, favorite players, cheer wall, quiz."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_fan_profile"
down_revision: Union[str, None] = "006_user_commerce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("secondary_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True))
    op.add_column("users", sa.Column("profile_completed", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("fan_cheers_total", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("fan_level", sa.Integer(), server_default="1", nullable=False))

    op.create_table(
        "user_favorite_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players_detailed.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "player_id", name="uq_user_fav_player"),
    )
    op.create_index("ix_user_fav_players_user", "user_favorite_players", ["user_id"])

    op.create_table(
        "team_cheers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_cheers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("match_id", "team_id", name="uq_team_cheers_match_team"),
    )

    op.create_table(
        "user_cheers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("coins_spent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cheer_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "match_id", name="uq_user_cheer_match"),
    )

    op.create_table(
        "fan_quiz_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_date", sa.Date(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("coins_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "quiz_date", name="uq_fan_quiz_user_date"),
    )


def downgrade() -> None:
    op.drop_table("fan_quiz_logs")
    op.drop_table("user_cheers")
    op.drop_table("team_cheers")
    op.drop_table("user_favorite_players")
    op.drop_column("users", "fan_level")
    op.drop_column("users", "fan_cheers_total")
    op.drop_column("users", "profile_completed")
    op.drop_column("users", "secondary_team_id")
