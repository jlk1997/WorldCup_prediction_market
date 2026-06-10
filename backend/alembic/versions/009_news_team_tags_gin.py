"""009: GIN index on news_articles.team_tags for team filter."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_news_tags_gin"
down_revision: Union[str, None] = "008_news_lang"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_news_articles_team_tags_gin",
        "news_articles",
        ["team_tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_news_articles_team_tags_gin", table_name="news_articles")
