"""014: orders pending lookup index."""

from alembic import op

revision = "014_orders_pending_idx"
down_revision = "013_commerce_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_orders_user_product_status",
        "orders",
        ["user_id", "product_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_orders_user_product_status", table_name="orders")
