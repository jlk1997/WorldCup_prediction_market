"""Add ai_analysis_jobs for crash recovery."""

import sqlalchemy as sa
from alembic import op

revision = "026_ai_analysis_jobs"
down_revision = "025_redeem_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_analysis_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team1", sa.String(100), nullable=False),
        sa.Column("team2", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(30), server_default="pre_match", nullable=False),
        sa.Column("force_refresh", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(20), server_default="running", nullable=False),
        sa.Column("billing_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_ai_analysis_jobs_user_id", "ai_analysis_jobs", ["user_id"])
    op.create_index("ix_ai_analysis_jobs_status", "ai_analysis_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ai_analysis_jobs_status", table_name="ai_analysis_jobs")
    op.drop_index("ix_ai_analysis_jobs_user_id", table_name="ai_analysis_jobs")
    op.drop_table("ai_analysis_jobs")
