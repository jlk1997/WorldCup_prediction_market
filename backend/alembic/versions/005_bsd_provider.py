"""005: external_provider on matches for BSD integration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_bsd_provider"
down_revision: Union[str, None] = "004_bracket_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("external_provider", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "external_provider")
