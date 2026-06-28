"""Post Phase 15: season_ultimate bundle SKU."""

from alembic import op
import sqlalchemy as sa

revision = "046_season_ultimate_matchday"
down_revision = "045_analytics_mint_bundle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, active, sort_order, featured, per_user_limit, grant_payload)
            SELECT 'season_ultimate', '赛季终极礼包', '通行证90天+手册尊享+金框主题+100球迷币，一季畅玩',
                16800, 100, 90, 'season_ultimate', 'cash', true, 79, true, 1,
                '{"collection_pass_premium": true, "collection_pass_level_skip": 5,
                  "avatar_frame": "gold_wc", "theme_key": "team_spirit",
                  "badge_code": "season_ultimate", "badge_title": "终极球迷"}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'season_ultimate')
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM products WHERE sku = 'season_ultimate'"))
