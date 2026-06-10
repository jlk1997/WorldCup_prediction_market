"""Agent force_refresh flag + platform token daily table."""

from alembic import op
import sqlalchemy as sa

revision = "015_security_hardening"
down_revision = "014_orders_pending_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("force_refresh", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "ai_platform_tokens_daily",
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("consumed", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("reserved", sa.BigInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_platform_tokens_daily")
    op.drop_column("agent_runs", "force_refresh")
