"""004: bracket_meta JSONB for knockout slot/feeder resolution."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_bracket_meta"
down_revision: Union[str, None] = "003_bracket_news"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("bracket_meta", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "bracket_meta")
