"""033: Collection Pass (藏品赛季手册) + collectible events."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "033_collection_pass"
down_revision: Union[str, None] = "032_collectible_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_pass_seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("max_level", sa.Integer(), server_default="40", nullable=False),
        sa.Column("config_json", JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "collection_pass_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("premium_unlocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("claimed_free_json", JSONB(), nullable=True),
        sa.Column("claimed_premium_json", JSONB(), nullable=True),
        sa.Column("xp_boost_until", sa.DateTime(), nullable=True),
        sa.Column("coin_shard_fill_today", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coin_shard_fill_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["collection_pass_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "season_id", name="uq_collection_pass_progress_user_season"),
    )
    op.create_index("ix_collection_pass_progress_user_id", "collection_pass_progress", ["user_id"])

    op.create_table(
        "collection_pass_xp_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("ref_type", sa.String(length=40), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["collection_pass_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "season_id", "source", "ref_type", "ref_id",
            name="uq_collection_pass_xp_idempotent",
        ),
    )
    op.create_index("ix_collection_pass_xp_logs_user_id", "collection_pass_xp_logs", ["user_id"])

    op.create_table(
        "collection_quest_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quest_key", sa.String(length=40), nullable=False),
        sa.Column("period_key", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("target", sa.Integer(), server_default="1", nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("xp_awarded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "quest_key", "period_key", name="uq_collection_quest_progress"),
    )
    op.create_index("ix_collection_quest_progress_user_id", "collection_quest_progress", ["user_id"])

    op.create_table(
        "collectible_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("event_series", sa.String(length=40), server_default="event_limited", nullable=False),
        sa.Column("boost_json", JSONB(), nullable=True),
        sa.Column("coin_action_cost", sa.Integer(), server_default="15", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # Seed season
    from datetime import datetime

    op.execute(
        sa.text(
            """
            INSERT INTO collection_pass_seasons (code, name, starts_at, ends_at, max_level, active, config_json)
            VALUES (
                'wc2026_s1',
                '2026 世界杯 · 藏品赛季手册',
                '2026-06-01 00:00:00',
                '2026-12-31 23:59:59',
                40,
                true,
                '{"premium_sku": "collection_pass"}'::jsonb
            )
            """
        )
    )

    # Seed collection pass product
    op.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days,
                product_type, pay_currency, per_user_limit, stock_total, stock_sold, active, sort_order, featured, grant_payload)
            SELECT
                'collection_pass',
                '藏品赛季手册 · 尊享版',
                '解锁尊享轨道全部确定性奖励（非随机盲盒）',
                4500,
                0,
                0,
                'collection_pass',
                'cash',
                1,
                0,
                0,
                true,
                15,
                true,
                '{"collection_pass_premium": true, "badge_code": "collection_pass_premium", "badge_title": "手册尊享"}'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'collection_pass')
            """
        )
    )

    # Seed default event (always-on demo window)
    op.execute(
        sa.text(
            """
            INSERT INTO collectible_events (code, name, description, starts_at, ends_at, event_series, boost_json, coin_action_cost, active)
            VALUES (
                'dark_horse_night',
                '黑马之夜',
                '活动期间应援可加权掉落限定卡',
                '2026-06-01 00:00:00',
                '2026-12-31 23:59:59',
                'event_limited',
                '{"forced_card_chance": 0.35, "series_weight": 3.0}'::jsonb,
                15,
                true
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM products WHERE sku = 'collection_pass'"))
    op.drop_table("collectible_events")
    op.drop_index("ix_collection_quest_progress_user_id", table_name="collection_quest_progress")
    op.drop_table("collection_quest_progress")
    op.drop_index("ix_collection_pass_xp_logs_user_id", table_name="collection_pass_xp_logs")
    op.drop_table("collection_pass_xp_logs")
    op.drop_index("ix_collection_pass_progress_user_id", table_name="collection_pass_progress")
    op.drop_table("collection_pass_progress")
    op.drop_table("collection_pass_seasons")
