"""008: news_articles.lang for zh/en sections."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_news_lang"
down_revision: Union[str, None] = "007_fan_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column("lang", sa.String(5), server_default="en", nullable=False),
    )
    op.create_index("ix_news_articles_lang_published", "news_articles", ["lang", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_news_articles_lang_published", table_name="news_articles")
    op.drop_column("news_articles", "lang")
