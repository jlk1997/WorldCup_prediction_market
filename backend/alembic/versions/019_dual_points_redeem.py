"""Dual points ledger (season + redeem) and redeem shop."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "019_dual_points_redeem"
down_revision = "018_referral_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("redeem_points", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("extra_free_predict_daily", sa.Integer(), server_default="0", nullable=False),
    )

    op.add_column(
        "point_ledger",
        sa.Column("point_bucket", sa.String(10), server_default="season", nullable=False),
    )
    op.create_index("ix_point_ledger_bucket_created", "point_ledger", ["point_bucket", "created_at"])

    op.add_column(
        "products",
        sa.Column("pay_currency", sa.String(10), server_default="cash", nullable=False),
    )
    op.add_column("products", sa.Column("redeem_price", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("grant_payload", JSONB(), nullable=True))
    op.add_column(
        "products",
        sa.Column("per_user_limit", sa.Integer(), server_default="0", nullable=False),
    )

    op.add_column(
        "game_predictions",
        sa.Column("redeem_points_awarded", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "redeem_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("redeem_price", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_redeem_orders_user_id", "redeem_orders", ["user_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                                  product_type, active, sort_order, pay_currency, redeem_price, grant_payload, per_user_limit)
            VALUES
            ('redeem_frame_gold', '世界杯金框', '兑换后获得专属头像金框', 0, 0, 0, 'redeem', true, 101, 'redeem', 400,
             '{"avatar_frame": "gold_wc"}'::jsonb, 1),
            ('redeem_theme_spirit', '主队 Spirit 主题', '兑换后获得主队主题色', 0, 0, 0, 'redeem', true, 102, 'redeem', 300,
             '{"theme_key": "team_spirit"}'::jsonb, 1),
            ('redeem_extra_free_predict', '每日额外免费竞猜 +1', '永久增加每日免费竞猜次数', 0, 0, 0, 'redeem', true, 103, 'redeem', 600,
             '{"extra_free_predict_daily": 1}'::jsonb, 1),
            ('redeem_badge_collector', '兑换达人徽章', '展示你的兑换成就', 0, 0, 0, 'redeem', true, 104, 'redeem', 200,
             '{"badge_code": "redeem_collector", "badge_title": "兑换达人"}'::jsonb, 1)
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM products WHERE sku IN "
            "('redeem_frame_gold', 'redeem_theme_spirit', 'redeem_extra_free_predict', 'redeem_badge_collector')"
        )
    )
    op.drop_index("ix_redeem_orders_user_id", table_name="redeem_orders")
    op.drop_table("redeem_orders")
    op.drop_column("game_predictions", "redeem_points_awarded")
    op.drop_column("products", "per_user_limit")
    op.drop_column("products", "grant_payload")
    op.drop_column("products", "redeem_price")
    op.drop_column("products", "pay_currency")
    op.drop_index("ix_point_ledger_bucket_created", table_name="point_ledger")
    op.drop_column("point_ledger", "point_bucket")
    op.drop_column("users", "extra_free_predict_daily")
    op.drop_column("users", "redeem_points")
