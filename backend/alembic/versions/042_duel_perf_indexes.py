"""042: 对决排行性能索引。"""

from typing import Sequence, Union

from alembic import op

revision: str = "042_duel_perf_indexes"
down_revision: Union[str, None] = "041_duel_elo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_duel_elo", "users", ["duel_elo"], unique=False)
    op.create_index("ix_card_duels_winner", "card_duels", ["winner_id"], unique=False)
    op.create_index("ix_card_duels_defender", "card_duels", ["defender_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_card_duels_defender", table_name="card_duels")
    op.drop_index("ix_card_duels_winner", table_name="card_duels")
    op.drop_index("ix_users_duel_elo", table_name="users")
