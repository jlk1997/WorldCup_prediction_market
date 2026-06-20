"""034: Golden boot event, collection pass plus bundle."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034_collection_pass_enrich"
down_revision: Union[str, None] = "033_collection_pass"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE collectible_events
            SET boost_json = COALESCE(boost_json, '{}'::jsonb) || '{"matchday_series_weight": 2.0}'::jsonb
            WHERE code = 'dark_horse_night'
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO collectible_events (code, name, description, starts_at, ends_at, event_series, boost_json, coin_action_cost, active)
            VALUES (
                'golden_boot',
                '金靴候选',
                '活动期间比赛日动员与应援加权掉落金靴限定卡',
                '2026-07-01 00:00:00',
                '2026-12-31 23:59:59',
                'event_limited',
                '{"forced_card_code": "event_limited_golden_boot", "forced_card_chance": 0.25, "series_weight": 4.0, "matchday_series_weight": 2.5}'::jsonb,
                20,
                true
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, per_user_limit, stock_total, stock_sold, active, sort_order, featured, grant_payload)
            SELECT
                'collection_pass_plus',
                '藏品赛季手册 · 尊享+越级10级',
                '解锁尊享轨道并直升10级（确定性奖励，非盲盒）',
                8800,
                0,
                0,
                'collection_pass',
                'cash',
                1,
                0,
                0,
                true,
                16,
                true,
                '{"collection_pass_premium": true, "collection_pass_level_skip": 10, "badge_code": "collection_pass_premium", "badge_title": "手册尊享"}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'collection_pass_plus')
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM products WHERE sku = 'collection_pass_plus'"))
    op.execute(sa.text("DELETE FROM collectible_events WHERE code = 'golden_boot'"))
