"""030: leaderboard season virtual reward awards."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "030_leaderboard_season_awards"
down_revision: Union[str, None] = "029_predict_reveal_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leaderboard_season_awards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("season_key", sa.String(length=20), nullable=False),
        sa.Column("board", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("season_points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coins_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("redeem_points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("awarded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "season_key", "board", name="uq_leaderboard_season_award"),
    )
    op.create_index(
        "ix_leaderboard_season_awards_season_board",
        "leaderboard_season_awards",
        ["season_key", "board"],
    )


def downgrade() -> None:
    op.drop_index("ix_leaderboard_season_awards_season_board", table_name="leaderboard_season_awards")
    op.drop_table("leaderboard_season_awards")
