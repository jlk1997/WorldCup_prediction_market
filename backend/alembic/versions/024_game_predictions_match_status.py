"""Pick stats query index for batch match distribution."""

from alembic import op

revision = "024_match_pick_idx"
down_revision = "023_user_signin_streak"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_game_predictions_match_status",
        "game_predictions",
        ["match_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_game_predictions_match_status", table_name="game_predictions")
