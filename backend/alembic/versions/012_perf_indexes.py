"""012: performance indexes for matches, predictions, sessions."""

from typing import Sequence, Union

from alembic import op

revision: str = "012_perf_indexes"
down_revision: Union[str, None] = "011_ai_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_matches_status", "matches", ["status"])
    op.create_index("ix_matches_match_date", "matches", ["match_date"])
    op.create_index("ix_game_predictions_status", "game_predictions", ["status"])
    op.create_index("ix_user_sessions_expires", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_refresh_hash", "user_sessions", ["refresh_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_refresh_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires", table_name="user_sessions")
    op.drop_index("ix_game_predictions_status", table_name="game_predictions")
    op.drop_index("ix_matches_match_date", table_name="matches")
    op.drop_index("ix_matches_status", table_name="matches")
