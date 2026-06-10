"""026: grant_payload for cash cosmetic product."""

from alembic import op

revision = "027_product_grant_payload"
down_revision = "026_ai_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE products
        SET grant_payload = '{"avatar_frame": "gold_wc", "theme_key": "team_spirit"}'::jsonb
        WHERE sku = 'team_cosmetic' AND (grant_payload IS NULL OR grant_payload = 'null'::jsonb)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE products SET grant_payload = NULL WHERE sku = 'team_cosmetic'
        """
    )
