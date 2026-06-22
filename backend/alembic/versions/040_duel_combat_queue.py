"""040: 卡牌对决战斗回放 + 快速匹配队列。"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "040_duel_combat_queue"
down_revision: Union[str, None] = "039_card_duel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("card_duel_logs", sa.Column("result_json", JSONB, nullable=True))
    op.add_column("card_duels", sa.Column("replay_json", JSONB, nullable=True))
    op.add_column("card_duels", sa.Column("ai_deck_json", JSONB, nullable=True))

    op.create_table(
        "card_duel_match_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_ids", JSONB, nullable=False),
        sa.Column("deck_bp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stake_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tier", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="waiting", nullable=False),
        sa.Column("duel_id", sa.Integer(), sa.ForeignKey("card_duels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("matched_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_duel_queue_user_status", "card_duel_match_queue", ["user_id", "status"])
    op.create_index("ix_duel_queue_waiting", "card_duel_match_queue", ["status", "tier"])


def downgrade() -> None:
    op.drop_index("ix_duel_queue_waiting", table_name="card_duel_match_queue")
    op.drop_index("ix_duel_queue_user_status", table_name="card_duel_match_queue")
    op.drop_table("card_duel_match_queue")
    op.drop_column("card_duels", "ai_deck_json")
    op.drop_column("card_duels", "replay_json")
    op.drop_column("card_duel_logs", "result_json")
