"""036: 足球数字资产平台 — 资产化字段、积分二级交易行、质押/阵容、首发打新、成就。

合规要点：二级流通一律以"可用积分"计价，人民币只进不出；新获卡牌冷却期后方可流通。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "036_football_asset_platform"
down_revision: Union[str, None] = "035_card_active_rarity_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: 实名认证（仅存哈希） ---
    op.add_column("users", sa.Column("real_name_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("real_name_hash", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("real_name_verified_at", sa.DateTime(), nullable=True))

    # --- user_collectible_cards: 资产化字段 ---
    op.add_column("user_collectible_cards", sa.Column("serial_no", sa.Integer(), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("mint_total", sa.Integer(), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("holding_until", sa.DateTime(), nullable=True))
    op.add_column("user_collectible_cards", sa.Column("tradable", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("user_collectible_cards", sa.Column("lock_state", sa.String(length=16), server_default="none", nullable=False))
    op.add_column("user_collectible_cards", sa.Column("acquired_value", sa.Integer(), server_default="0", nullable=False))

    # --- card_serial_counters ---
    op.create_table(
        "card_serial_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("issued", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", name="uq_card_serial_counter_card"),
    )

    # --- card_transfer_logs ---
    op.create_table(
        "card_transfer_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("user_card_id", sa.Integer(), nullable=True),
        sa.Column("from_user_id", sa.Integer(), nullable=True),
        sa.Column("to_user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("points_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fee_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chain_status", sa.String(length=20), server_default="none", nullable=False),
        sa.Column("chain_operation_id", sa.String(length=64), nullable=True),
        sa.Column("chain_tx_hash", sa.String(length=128), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_transfer_logs_card_id", "card_transfer_logs", ["card_id"])
    op.create_index("ix_card_transfer_logs_created_at", "card_transfer_logs", ["created_at"])

    # --- card_listings ---
    op.create_table(
        "card_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("user_card_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("list_type", sa.String(length=12), server_default="fixed", nullable=False),
        sa.Column("price_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("min_increment", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_bid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_bidder_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("sold_to_id", sa.Integer(), nullable=True),
        sa.Column("sold_price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_card_id"], ["user_collectible_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_bidder_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sold_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_listings_seller_id", "card_listings", ["seller_id"])
    op.create_index("ix_card_listings_card_id", "card_listings", ["card_id"])
    op.create_index("ix_card_listings_expires_at", "card_listings", ["expires_at"])
    op.create_index("ix_card_listings_status", "card_listings", ["status"])

    # --- market_bids ---
    op.create_table(
        "market_bids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("bidder_id", sa.Integer(), nullable=False),
        sa.Column("amount_points", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["card_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bidder_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_bids_listing_id", "market_bids", ["listing_id"])
    op.create_index("ix_market_bids_bidder_id", "market_bids", ["bidder_id"])

    # --- market_price_points ---
    op.create_table(
        "market_price_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("price_points", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), server_default="1", nullable=False),
        sa.Column("kind", sa.String(length=12), server_default="trade", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_price_points_card_id", "market_price_points", ["card_id"])
    op.create_index("ix_market_price_points_created_at", "market_price_points", ["created_at"])

    # --- card_stakes ---
    op.create_table(
        "card_stakes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_card_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("rarity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="active", nullable=False),
        sa.Column("staked_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_claim_at", sa.DateTime(), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("total_claimed", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_card_id"], ["user_collectible_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_stakes_user_id", "card_stakes", ["user_id"])

    # --- fantasy_lineups ---
    op.create_table(
        "fantasy_lineups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_key", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=60), server_default="我的阵容", nullable=False),
        sa.Column("slots_json", JSONB(), nullable=True),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rewarded", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "period_key", name="uq_fantasy_lineup_user_period"),
    )
    op.create_index("ix_fantasy_lineups_user_id", "fantasy_lineups", ["user_id"])

    # --- fantasy_score_logs ---
    op.create_table(
        "fantasy_score_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lineup_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("detail_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lineup_id"], ["fantasy_lineups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lineup_id", "match_id", name="uq_fantasy_score_lineup_match"),
    )
    op.create_index("ix_fantasy_score_logs_lineup_id", "fantasy_score_logs", ["lineup_id"])

    # --- mint_events ---
    op.create_table(
        "mint_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("card_code", sa.String(length=80), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("rarity", sa.String(length=20), server_default="epic", nullable=False),
        sa.Column("competition", sa.String(length=40), nullable=True),
        sa.Column("total_supply", sa.Integer(), nullable=False),
        sa.Column("issued", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="coins", nullable=False),
        sa.Column("price_coins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("price_fen", sa.Integer(), server_default="0", nullable=False),
        sa.Column("per_user_limit", sa.Integer(), server_default="1", nullable=False),
        sa.Column("sale_mode", sa.String(length=16), server_default="public", nullable=False),
        sa.Column("reserve_starts_at", sa.DateTime(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="scheduled", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_mint_event_code"),
    )

    # --- mint_reservations ---
    op.create_table(
        "mint_reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="reserved", nullable=False),
        sa.Column("claimed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["mint_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_mint_reservation_event_user"),
    )
    op.create_index("ix_mint_reservations_event_id", "mint_reservations", ["event_id"])
    op.create_index("ix_mint_reservations_user_id", "mint_reservations", ["user_id"])

    # --- user_achievements ---
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "code", name="uq_user_achievement"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_achievements")
    op.drop_table("mint_reservations")
    op.drop_table("mint_events")
    op.drop_table("fantasy_score_logs")
    op.drop_table("fantasy_lineups")
    op.drop_table("card_stakes")
    op.drop_table("market_price_points")
    op.drop_table("market_bids")
    op.drop_table("card_listings")
    op.drop_table("card_transfer_logs")
    op.drop_table("card_serial_counters")

    op.drop_column("user_collectible_cards", "acquired_value")
    op.drop_column("user_collectible_cards", "lock_state")
    op.drop_column("user_collectible_cards", "tradable")
    op.drop_column("user_collectible_cards", "holding_until")
    op.drop_column("user_collectible_cards", "mint_total")
    op.drop_column("user_collectible_cards", "serial_no")

    op.drop_column("users", "real_name_verified_at")
    op.drop_column("users", "real_name_hash")
    op.drop_column("users", "real_name_verified")
