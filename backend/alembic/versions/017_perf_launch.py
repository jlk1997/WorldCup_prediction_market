"""Launch performance indexes."""

from alembic import op

revision = "017_perf_launch"
down_revision = "016_user_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_matches_external_fixture_id", "matches", ["external_fixture_id"], unique=False)
    op.create_index("ix_matches_status_date", "matches", ["status", "match_date"], unique=False)
    op.create_index("ix_game_predictions_status_match", "game_predictions", ["status", "match_id"], unique=False)
    op.create_index("ix_agent_runs_mode_created", "agent_runs", ["mode", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_runs_mode_created", table_name="agent_runs")
    op.drop_index("ix_game_predictions_status_match", table_name="game_predictions")
    op.drop_index("ix_matches_status_date", table_name="matches")
    op.drop_index("ix_matches_external_fixture_id", table_name="matches")
