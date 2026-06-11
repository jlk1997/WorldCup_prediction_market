"""028: indexes for team name lookup and user prediction queries."""

from typing import Sequence, Union

from alembic import op

revision: str = "028_query_indexes"
down_revision: Union[str, None] = "027_product_grant_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)
    op.create_index(
        "ix_game_predictions_user_status",
        "game_predictions",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_game_predictions_user_status", table_name="game_predictions")
    op.drop_index("ix_teams_name", table_name="teams")
