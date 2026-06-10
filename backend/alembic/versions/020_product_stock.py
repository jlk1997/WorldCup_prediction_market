"""Product global stock for redeem shop."""

from alembic import op
import sqlalchemy as sa

revision = "020_product_stock"
down_revision = "019_dual_points_redeem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("stock_total", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "products",
        sa.Column("stock_sold", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        sa.text(
            """
            UPDATE products p
            SET stock_sold = COALESCE((
                SELECT COUNT(*)::int FROM redeem_orders r
                WHERE r.product_id = p.id AND r.status = 'completed'
            ), 0)
            """
        )
    )
    # 限量示例：兑换达人徽章全服 500 份（0 = 不限量）
    op.execute(
        sa.text(
            """
            UPDATE products SET stock_total = 500
            WHERE sku = 'redeem_badge_collector' AND pay_currency = 'redeem'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("products", "stock_sold")
    op.drop_column("products", "stock_total")
