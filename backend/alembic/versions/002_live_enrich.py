"""002: live match fields + data_sync_logs + news/agent tables (phase 1-3)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_live_enrich"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("external_fixture_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("status", sa.String(30), server_default="scheduled"))
    op.add_column("matches", sa.Column("home_score", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("away_score", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("minute", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("period", sa.String(20), nullable=True))
    op.add_column("matches", sa.Column("events_json", postgresql.JSONB(), nullable=True))
    op.add_column("matches", sa.Column("live_updated_at", sa.DateTime(), nullable=True))

    op.create_table(
        "data_sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("ran_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.add_column("players_detailed", sa.Column("injury_status", sa.String(50), nullable=True))
    op.add_column("players_detailed", sa.Column("injury_detail", sa.Text(), nullable=True))
    op.add_column("players_detailed", sa.Column("last_seen_at", sa.DateTime(), nullable=True))
    op.add_column("players_detailed", sa.Column("market_value", sa.String(50), nullable=True))
    op.add_column("players_detailed", sa.Column("form_rating", sa.Integer(), nullable=True))

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), unique=True),
        sa.Column("source", sa.String(100)),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("team_tags", postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("team1", sa.String(100)),
        sa.Column("team2", sa.String(100)),
        sa.Column("mode", sa.String(30), server_default="pre_match"),
        sa.Column("steps_json", postgresql.JSONB(), nullable=True),
        sa.Column("final_output", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("news_articles")
    op.drop_column("players_detailed", "form_rating")
    op.drop_column("players_detailed", "market_value")
    op.drop_column("players_detailed", "last_seen_at")
    op.drop_column("players_detailed", "injury_detail")
    op.drop_column("players_detailed", "injury_status")
    op.drop_table("data_sync_logs")
    for col in ("live_updated_at", "events_json", "period", "minute", "away_score", "home_score", "status", "external_fixture_id"):
        op.drop_column("matches", col)
