"""043: 人民币打新订单关联与库存锁。"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "043_rmb_mint_orders"
down_revision: Union[str, None] = "042_duel_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("mint_event_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_orders_mint_event_id",
        "orders",
        "mint_events",
        ["mint_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("orders", sa.Column("grant_result_json", JSONB, nullable=True))
    op.create_index("ix_orders_mint_event_status", "orders", ["mint_event_id", "status"], unique=False)

    op.add_column("mint_reservations", sa.Column("pending_order_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_mint_reservations_pending_order_id",
        "mint_reservations",
        "orders",
        ["pending_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("mint_reservations", sa.Column("lock_expires_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_mint_reservations_payment_pending",
        "mint_reservations",
        ["event_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mint_reservations_payment_pending", table_name="mint_reservations")
    op.drop_constraint("fk_mint_reservations_pending_order_id", "mint_reservations", type_="foreignkey")
    op.drop_column("mint_reservations", "lock_expires_at")
    op.drop_column("mint_reservations", "pending_order_id")

    op.drop_index("ix_orders_mint_event_status", table_name="orders")
    op.drop_constraint("fk_orders_mint_event_id", "orders", type_="foreignkey")
    op.drop_column("orders", "grant_result_json")
    op.drop_column("orders", "mint_event_id")
