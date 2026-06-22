"""038: Fantasy 周榜结算记录。"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "038_fantasy_weekly_reward"
down_revision: Union[str, None] = "037_allow_split_collectible_rows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fantasy_weekly_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_key", sa.String(length=20), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coins_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("settled_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "period_key", name="uq_fantasy_weekly_settlement_user_period"),
    )
    op.create_index("ix_fantasy_weekly_settlements_period", "fantasy_weekly_settlements", ["period_key"])


def downgrade() -> None:
    op.drop_index("ix_fantasy_weekly_settlements_period", table_name="fantasy_weekly_settlements")
    op.drop_table("fantasy_weekly_settlements")
