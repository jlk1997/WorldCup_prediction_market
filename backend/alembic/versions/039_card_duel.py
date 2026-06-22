"""039: 卡牌对决 PVP。"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "039_card_duel"
down_revision: Union[str, None] = "038_fantasy_weekly_reward"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "card_duels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("challenger_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("defender_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mode", sa.String(length=16), server_default="ai", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("challenger_card_ids", JSONB, nullable=False),
        sa.Column("defender_card_ids", JSONB, nullable=True),
        sa.Column("stake_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("challenger_power", sa.Integer(), server_default="0", nullable=False),
        sa.Column("defender_power", sa.Integer(), server_default="0", nullable=False),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_card_duels_challenger", "card_duels", ["challenger_id"])
    op.create_index("ix_card_duels_status", "card_duels", ["status"])

    op.create_table(
        "card_duel_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("duel_id", sa.Integer(), sa.ForeignKey("card_duels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("challenger_power", sa.Integer(), nullable=False),
        sa.Column("defender_power", sa.Integer(), nullable=False),
        sa.Column("winner_side", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("card_duel_logs")
    op.drop_index("ix_card_duels_status", table_name="card_duels")
    op.drop_index("ix_card_duels_challenger", table_name="card_duels")
    op.drop_table("card_duels")
