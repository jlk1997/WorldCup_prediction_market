"""Redeem order idempotency key for safe retries."""

from alembic import op
import sqlalchemy as sa

revision = "021_redeem_idempotency"
down_revision = "020_product_stock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("redeem_orders", sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_redeem_order_idempotency",
        "redeem_orders",
        ["user_id", "idempotency_key"],
    )
    op.execute(
        sa.text(
            """
            UPDATE products SET stock_total = 200
            WHERE sku = 'redeem_extra_free_predict' AND pay_currency = 'redeem' AND stock_total = 0
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("uq_redeem_order_idempotency", "redeem_orders", type_="unique")
    op.drop_column("redeem_orders", "idempotency_key")
