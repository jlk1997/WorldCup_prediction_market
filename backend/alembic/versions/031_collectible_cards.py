"""031: collectible cards / digital collectibles system."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "031_collectible_cards"
down_revision: Union[str, None] = "030_leaderboard_season_awards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collectible_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("rarity", sa.String(length=20), nullable=False),
        sa.Column("series", sa.String(length=40), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("attributes_json", JSONB(), nullable=True),
        sa.Column("is_limited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("available_from", sa.DateTime(), nullable=True),
        sa.Column("available_until", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players_detailed.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_collectible_cards_rarity", "collectible_cards", ["rarity"])
    op.create_index("ix_collectible_cards_team_id", "collectible_cards", ["team_id"])

    op.create_table(
        "user_collectible_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("star", sa.Integer(), server_default="1", nullable=False),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("highlight_json", JSONB(), nullable=True),
        sa.Column("obtained_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["collectible_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_user_collectible_card"),
    )
    op.create_index("ix_user_collectible_cards_user_id", "user_collectible_cards", ["user_id"])

    op.create_table(
        "collectible_shards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rarity", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "rarity", name="uq_collectible_shard_user_rarity"),
    )

    op.create_table(
        "card_set_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("card_codes", JSONB(), nullable=False),
        sa.Column("reward_json", JSONB(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "card_set_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=False),
        sa.Column("claimed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["set_id"], ["card_set_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "set_id", name="uq_card_set_progress_user_set"),
    )

    op.create_table(
        "collectible_drop_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=False),
        sa.Column("result_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source", "ref_type", "ref_id", name="uq_collectible_drop_idempotent"),
    )
    op.create_index("ix_collectible_drop_logs_user_id", "collectible_drop_logs", ["user_id"])

    _seed_catalog()


def _seed_catalog() -> None:
    from sqlalchemy.orm import Session

    from app.data.collectible_catalog import build_card_catalog
    from app.db.models.commerce import CardSetDefinition, CollectibleCard

    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        card_defs, set_defs = build_card_catalog(session)
        for cdef in card_defs:
            existing = session.query(CollectibleCard).filter(CollectibleCard.code == cdef["code"]).first()
            if existing:
                continue
            session.add(
                CollectibleCard(
                    code=cdef["code"],
                    player_id=cdef.get("player_id"),
                    team_id=cdef.get("team_id"),
                    name=cdef["name"],
                    rarity=cdef["rarity"],
                    series=cdef["series"],
                    image_url=cdef.get("image_url"),
                    attributes_json=cdef.get("attributes_json"),
                    is_limited=cdef.get("is_limited", False),
                    sort_order=cdef.get("sort_order", 0),
                    active=True,
                )
            )
        for sdef in set_defs:
            existing = session.query(CardSetDefinition).filter(CardSetDefinition.code == sdef["code"]).first()
            if existing:
                continue
            session.add(
                CardSetDefinition(
                    code=sdef["code"],
                    name=sdef["name"],
                    description=sdef.get("description"),
                    card_codes=sdef["card_codes"],
                    reward_json=sdef.get("reward_json"),
                    sort_order=sdef.get("sort_order", 0),
                    active=True,
                )
            )
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    op.drop_index("ix_collectible_drop_logs_user_id", table_name="collectible_drop_logs")
    op.drop_table("collectible_drop_logs")
    op.drop_table("card_set_progress")
    op.drop_table("card_set_definitions")
    op.drop_table("collectible_shards")
    op.drop_index("ix_user_collectible_cards_user_id", table_name="user_collectible_cards")
    op.drop_table("user_collectible_cards")
    op.drop_index("ix_collectible_cards_team_id", table_name="collectible_cards")
    op.drop_index("ix_collectible_cards_rarity", table_name="collectible_cards")
    op.drop_table("collectible_cards")
