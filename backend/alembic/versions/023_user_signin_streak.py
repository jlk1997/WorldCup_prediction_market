"""User signin streak for daily ritual."""

from alembic import op
import sqlalchemy as sa

revision = "023_user_signin_streak"
down_revision = "022_product_stock_check"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("signin_streak", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("referral_tier_granted", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("loss_streak", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("free_cheer_tickets", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "free_cheer_tickets")
    op.drop_column("users", "loss_streak")
    op.drop_column("users", "referral_tier_granted")
    op.drop_column("users", "signin_streak")
