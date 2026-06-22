"""041: 卡牌对决 ELO 排位。"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "041_duel_elo"
down_revision: Union[str, None] = "040_duel_combat_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("duel_elo", sa.Integer(), server_default="1000", nullable=False))
    op.add_column("card_duels", sa.Column("challenger_elo_delta", sa.Integer(), server_default="0", nullable=False))
    op.add_column("card_duels", sa.Column("defender_elo_delta", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("card_duels", "defender_elo_delta")
    op.drop_column("card_duels", "challenger_elo_delta")
    op.drop_column("users", "duel_elo")
