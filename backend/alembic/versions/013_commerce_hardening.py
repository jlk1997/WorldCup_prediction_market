"""013: align season pass product copy; game_predictions user+status index."""

from alembic import op

revision = "013_commerce_hardening"
down_revision = "012_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE products
        SET description = '30天每日+50币、积分1.2x、额外AI免费次数'
        WHERE sku = 'season_pass'
        """
    )
    op.create_index(
        "ix_game_predictions_user_status",
        "game_predictions",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_game_predictions_user_status", table_name="game_predictions")
    op.execute(
        """
        UPDATE products
        SET description = '30天每日+50币、积分1.2x'
        WHERE sku = 'season_pass'
        """
    )
