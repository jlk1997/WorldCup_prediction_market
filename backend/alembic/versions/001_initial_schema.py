"""Initial schema for WC2026."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("country_code", sa.String(10), nullable=False),
        sa.Column("fifa_ranking", sa.Integer()),
        sa.Column("group_name", sa.String(10)),
        sa.Column("coach", sa.String(100)),
        sa.Column("total_value", sa.String(50)),
        sa.Column("avg_age", sa.Numeric(4, 1)),
        sa.Column("formation", sa.String(50)),
        sa.Column("logo_url", sa.Text()),
        sa.Column("founded", sa.String(50)),
        sa.Column("city", sa.String(100)),
        sa.Column("stadium", sa.String(100)),
        sa.Column("capacity", sa.String(50)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("jersey_number", sa.Integer()),
        sa.Column("is_key_player", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "players_detailed",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("position", sa.String(50)),
        sa.Column("club", sa.String(100)),
        sa.Column("is_starter", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("description", sa.Text()),
        sa.Column("height", sa.Integer()),
        sa.Column("weight", sa.Integer()),
        sa.Column("preferred_foot", sa.String(20)),
        sa.Column("birth_date", sa.String(50)),
        sa.Column("overall_rating", sa.Integer()),
        sa.Column("stats", postgresql.JSONB()),
        sa.Column("honors", postgresql.JSONB()),
        sa.Column("transfers", postgresql.JSONB()),
        sa.Column("injuries", postgresql.JSONB()),
    )
    op.create_index("ix_players_detailed_team_rating", "players_detailed", ["team_id", "overall_rating"])
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_name", sa.String(50)),
        sa.Column("match_date", sa.String(50)),
        sa.Column("match_time", sa.String(20)),
        sa.Column("team1_name", sa.String(100)),
        sa.Column("team2_name", sa.String(100)),
        sa.Column("stadium", sa.String(200)),
    )
    op.create_table(
        "match_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team1", sa.String(100)),
        sa.Column("team2", sa.String(100)),
        sa.Column("total_goals", sa.String(100)),
        sa.Column("red_cards", sa.String(100)),
        sa.Column("penalties", sa.String(200)),
        sa.Column("score", sa.String(100)),
        sa.Column("advice", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("team1", "team2", name="uq_match_predictions_teams"),
    )


def downgrade() -> None:
    op.drop_table("match_predictions")
    op.drop_table("matches")
    op.drop_index("ix_players_detailed_team_rating", table_name="players_detailed")
    op.drop_table("players_detailed")
    op.drop_table("players")
    op.drop_table("teams")
