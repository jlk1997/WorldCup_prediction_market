"""Products updated_at/featured for redeem shop admin."""

import json

import sqlalchemy as sa
from alembic import op

revision = "025_redeem_admin"
down_revision = "024_match_pick_idx"
branch_labels = None
depends_on = None

_DEFAULT_REDEEM = [
    {
        "sku": "redeem_frame_silver",
        "name": "银框球迷",
        "description": "300 可用积分即可兑换的入门头像框",
        "redeem_price": 300,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 5,
        "grant_payload": {"avatar_frame": "silver_wc"},
    },
    {
        "sku": "redeem_frame_gold",
        "name": "世界杯金框",
        "description": "专属头像金框，彰显世界杯球迷身份",
        "redeem_price": 400,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 10,
        "grant_payload": {"avatar_frame": "gold_wc"},
    },
    {
        "sku": "redeem_theme_spirit",
        "name": "主队 Spirit 主题",
        "description": "全站金色主题色，与主队精神共鸣",
        "redeem_price": 300,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 20,
        "grant_payload": {"theme_key": "team_spirit"},
    },
    {
        "sku": "redeem_extra_free_predict",
        "name": "每日额外免费竞猜 +1",
        "description": "永久增加 1 次每日免费竞猜额度",
        "redeem_price": 600,
        "per_user_limit": 1,
        "stock_total": 200,
        "sort_order": 30,
        "grant_payload": {"extra_free_predict_daily": 1},
    },
    {
        "sku": "redeem_badge_collector",
        "name": "兑换达人徽章",
        "description": "积分商城专属荣誉徽章",
        "redeem_price": 200,
        "per_user_limit": 1,
        "stock_total": 500,
        "sort_order": 40,
        "grant_payload": {"badge_code": "redeem_collector", "badge_title": "兑换达人"},
    },
]


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("featured", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "products",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )

    conn = op.get_bind()
    count = conn.execute(
        sa.text("SELECT COUNT(*) FROM products WHERE pay_currency = 'redeem'")
    ).scalar()
    if count and int(count) > 0:
        return

    for item in _DEFAULT_REDEEM:
        conn.execute(
            sa.text(
                """
                INSERT INTO products (
                    sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                    product_type, pay_currency, redeem_price, grant_payload,
                    per_user_limit, stock_total, stock_sold, active, sort_order, featured
                ) VALUES (
                    :sku, :name, :description, 0, 0, 0,
                    'redeem', 'redeem', :redeem_price, CAST(:grant_payload AS jsonb),
                    :per_user_limit, :stock_total, 0, true, :sort_order, false
                )
                """
            ),
            {
                "sku": item["sku"],
                "name": item["name"],
                "description": item.get("description"),
                "redeem_price": item["redeem_price"],
                "grant_payload": json.dumps(item.get("grant_payload") or {}),
                "per_user_limit": item.get("per_user_limit") or 0,
                "stock_total": item.get("stock_total") or 0,
                "sort_order": item.get("sort_order") or 0,
            },
        )


def downgrade() -> None:
    op.drop_column("products", "updated_at")
    op.drop_column("products", "featured")
