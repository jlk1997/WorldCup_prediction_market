"""Phase 11-15: AI pack credits, battalion room goals, ai_pack products."""

from alembic import op
import sqlalchemy as sa

revision = "044_ecosystem_phase11_15"
down_revision = "043_rmb_mint_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ai_pack_live_credits", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("ai_pack_refresh_credits", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "battalion_room_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_key", sa.String(20), server_default="wc2026", nullable=False),
        sa.Column("goal_type", sa.String(30), nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("current_value", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reward_card_code", sa.String(80), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.UniqueConstraint("team_id", "season_key", "goal_type", name="uq_battalion_room_goal"),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, active, sort_order, grant_payload)
            SELECT 'ai_pack_live_10', 'AI 赛中分析 10 次包', '含 10 次 live 模式 AI 分析额度，持卡仍享折扣',
                1800, 0, 0, 'ai_pack', 'cash', true, 85,
                '{"ai_live_credits": 10}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'ai_pack_live_10')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, active, sort_order, grant_payload)
            SELECT 'ai_pack_refresh_5', 'AI 强制刷新 5 次包', '含 5 次 AI 强制刷新额度',
                1200, 0, 0, 'ai_pack', 'cash', true, 86,
                '{"ai_refresh_credits": 5}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'ai_pack_refresh_5')
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM products WHERE sku IN ('ai_pack_live_10', 'ai_pack_refresh_5')"))
    op.drop_table("battalion_room_goals")
    op.drop_column("users", "ai_pack_refresh_credits")
    op.drop_column("users", "ai_pack_live_credits")
