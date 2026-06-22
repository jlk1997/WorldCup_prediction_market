"""037: 允许同一用户持有多条同款卡牌（叠卡拆分后独立流通）。"""

from typing import Sequence, Union

from alembic import op

revision: str = "037_allow_split_collectible_rows"
down_revision: Union[str, None] = "036_football_asset_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_user_collectible_card", "user_collectible_cards", type_="unique")
    op.create_index("ix_user_collectible_cards_user_card", "user_collectible_cards", ["user_id", "card_id"])


def downgrade() -> None:
    op.drop_index("ix_user_collectible_cards_user_card", table_name="user_collectible_cards")
    op.create_unique_constraint("uq_user_collectible_card", "user_collectible_cards", ["user_id", "card_id"])
