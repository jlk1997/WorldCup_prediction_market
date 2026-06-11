"""028: index for team name lookup (predictions user+status index already in 013)."""

from typing import Sequence, Union

from alembic import op

revision: str = "028_query_indexes"
down_revision: Union[str, None] = "027_product_grant_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ix_game_predictions_user_status was added in 013_commerce_hardening — do not recreate.
    op.execute("CREATE INDEX IF NOT EXISTS ix_teams_name ON teams (name)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_teams_name")
