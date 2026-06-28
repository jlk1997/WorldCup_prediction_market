"""Phase 11+ continuation: product analytics events + mint_bundle SKU."""

from alembic import op
import sqlalchemy as sa

revision = "045_analytics_mint_bundle"
down_revision = "044_ecosystem_phase11_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_name", sa.String(80), nullable=False, index=True),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, active, sort_order, grant_payload)
            SELECT 'mint_bundle_starter', '打新组合包', '限量打新资格券占位+50球迷币+1次AI live额度',
                8800, 50, 0, 'mint_bundle', 'cash', true, 84,
                '{"ai_live_credits": 1, "mint_coupon_note": "运营配置具体打新活动"}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'mint_bundle_starter')
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM products WHERE sku = 'mint_bundle_starter'"))
    op.drop_table("product_analytics_events")
