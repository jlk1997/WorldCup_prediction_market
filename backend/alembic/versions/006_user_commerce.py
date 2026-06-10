"""006: users, auth, game predictions, commerce."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_user_commerce"
down_revision: Union[str, None] = "005_bsd_provider"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("nickname", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("fan_coins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("season_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("win_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("favorite_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("has_season_pass", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("season_pass_until", sa.DateTime(), nullable=True),
        sa.Column("last_signin_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_codes_email", "auth_codes", ["email"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "coin_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("ref_type", sa.String(30), nullable=True),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_coin_ledger_user", "coin_ledger", ["user_id"])

    op.create_table(
        "point_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("ref_type", sa.String(30), nullable=True),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_point_ledger_user", "point_ledger", ["user_id"])

    op.create_table(
        "game_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("market_type", sa.String(20), server_default="1x2", nullable=False),
        sa.Column("pick", sa.String(10), nullable=False),
        sa.Column("stake_coins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_free", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coins_returned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "match_id", name="uq_game_pred_user_match"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_fen", sa.Integer(), nullable=False),
        sa.Column("coins_grant", sa.Integer(), server_default="0", nullable=False),
        sa.Column("grant_season_pass_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("product_type", sa.String(30), server_default="coins", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("out_trade_no", sa.String(64), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("amount_fen", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("alipay_trade_no", sa.String(64), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "payment_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("out_trade_no", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("awarded_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),
    )

    op.add_column("agent_runs", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))

    # seed products
    op.execute(
        sa.text(
            """
            INSERT INTO products (sku, name, description, price_fen, coins_grant, grant_season_pass_days, product_type, sort_order)
            VALUES
            ('coins_small', '球迷币·小包', '60 球迷币', 600, 60, 0, 'coins', 1),
            ('coins_medium', '球迷币·中包', '350 球迷币', 3000, 350, 0, 'coins', 2),
            ('coins_large', '球迷币·大包', '1200 球迷币', 9800, 1200, 0, 'coins', 3),
            ('season_pass', '赛季竞猜通行证', '30天每日+50币、积分1.2x', 6800, 0, 30, 'season_pass', 4),
            ('team_cosmetic', '主队装扮包', '头像框+主题色', 1200, 50, 0, 'cosmetic', 5)
            """
        )
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "user_id")
    op.drop_table("user_badges")
    op.drop_table("payment_notifications")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("game_predictions")
    op.drop_table("point_ledger")
    op.drop_table("coin_ledger")
    op.drop_table("user_sessions")
    op.drop_table("auth_codes")
    op.drop_table("users")
