"""035: composite index on collectible_cards (active, rarity) for drop/synthesis queries."""

from typing import Sequence, Union

from alembic import op

revision: str = "035_card_active_rarity_idx"
down_revision: Union[str, None] = "034_collection_pass_enrich"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_collectible_cards_active_rarity",
        "collectible_cards",
        ["active", "rarity"],
    )


def downgrade() -> None:
    op.drop_index("ix_collectible_cards_active_rarity", table_name="collectible_cards")
