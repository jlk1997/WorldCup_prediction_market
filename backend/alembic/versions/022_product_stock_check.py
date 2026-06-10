"""CHECK constraint: stock_sold cannot exceed stock_total when limited."""

from alembic import op
import sqlalchemy as sa

revision = "022_product_stock_check"
down_revision = "021_redeem_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_products_stock_sold_lte_total",
        "products",
        "stock_total = 0 OR stock_sold <= stock_total",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_stock_sold_lte_total", "products", type_="check")
