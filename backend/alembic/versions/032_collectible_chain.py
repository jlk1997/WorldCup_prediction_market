"""032: AVATA / 文昌链 chain fields for collectibles."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032_collectible_chain"
down_revision: Union[str, None] = "031_collectible_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_collectible_cards",
        sa.Column("chain_status", sa.String(length=20), server_default="none", nullable=False),
    )
    op.add_column("user_collectible_cards", sa.Column("chain_operation_id", sa.String(length=64), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("chain_class_id", sa.String(length=128), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("chain_nft_id", sa.String(length=128), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("chain_tx_hash", sa.String(length=128), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("chain_minted_at", sa.DateTime(), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("chain_error", sa.Text(), nullable=True))
    op.create_index("ix_user_collectible_cards_chain_status", "user_collectible_cards", ["chain_status"])

    op.create_table(
        "user_chain_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("native_address", sa.String(length=128), nullable=True),
        sa.Column("hex_address", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=20), server_default="avata", nullable=False),
        sa.Column("chain_name", sa.String(length=40), server_default="文昌链", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("operation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_chain_account_user"),
    )
    op.create_index("ix_user_chain_accounts_user_id", "user_chain_accounts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_chain_accounts_user_id", table_name="user_chain_accounts")
    op.drop_table("user_chain_accounts")
    op.drop_index("ix_user_collectible_cards_chain_status", table_name="user_collectible_cards")
    op.drop_column("user_collectible_cards", "chain_error")
    op.drop_column("user_collectible_cards", "chain_minted_at")
    op.drop_column("user_collectible_cards", "chain_tx_hash")
    op.drop_column("user_collectible_cards", "chain_nft_id")
    op.drop_column("user_collectible_cards", "chain_class_id")
    op.drop_column("user_collectible_cards", "chain_operation_id")
    op.drop_column("user_collectible_cards", "chain_status")
