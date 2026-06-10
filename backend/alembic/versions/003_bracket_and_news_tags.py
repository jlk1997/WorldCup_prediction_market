"""003: bracket columns on matches + news team_tags JSONB alignment."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_bracket_news"
down_revision: Union[str, None] = "002_live_enrich"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("round_type", sa.String(20), server_default="group"))
    op.add_column("matches", sa.Column("bracket_round", sa.String(30), nullable=True))
    op.add_column("matches", sa.Column("bracket_order", sa.Integer(), nullable=True))

    op.execute(
        """
        ALTER TABLE news_articles
        ALTER COLUMN team_tags TYPE JSONB
        USING CASE
            WHEN team_tags IS NULL THEN NULL
            ELSE to_jsonb(team_tags)
        END
        """
    )


def downgrade() -> None:
    op.drop_column("matches", "bracket_order")
    op.drop_column("matches", "bracket_round")
    op.drop_column("matches", "round_type")
    op.execute(
        """
        ALTER TABLE news_articles
        ALTER COLUMN team_tags TYPE VARCHAR(100)[]
        USING CASE
            WHEN team_tags IS NULL THEN NULL
            ELSE ARRAY(SELECT jsonb_array_elements_text(team_tags))
        END
        """
    )
