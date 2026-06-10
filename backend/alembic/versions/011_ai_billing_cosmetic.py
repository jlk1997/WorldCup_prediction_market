"""011: AI usage daily tracking + user cosmetic / season pass daily."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_ai_billing"
down_revision: Union[str, None] = "010_arena_battalion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("free_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("paid_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_total", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_daily"),
    )
    op.add_column("users", sa.Column("avatar_frame", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("theme_key", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("last_season_pass_daily", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_season_pass_daily")
    op.drop_column("users", "theme_key")
    op.drop_column("users", "avatar_frame")
    op.drop_table("ai_usage_daily")
