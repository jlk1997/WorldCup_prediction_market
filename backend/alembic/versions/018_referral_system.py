"""Referral / invite system tables."""

from alembic import op
import sqlalchemy as sa

revision = "018_referral_system"
down_revision = "017_perf_launch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("invite_code", sa.String(12), nullable=True))
    op.add_column("users", sa.Column("referred_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_referred_by",
        "users",
        "users",
        ["referred_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_invite_code", "users", ["invite_code"], unique=True)

    op.create_table(
        "referral_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inviter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invitee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invite_code_used", sa.String(12), nullable=False),
        sa.Column("same_team_bonus_applied", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("registered_ip", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("invitee_id", name="uq_referral_binding_invitee"),
    )
    op.create_index("ix_referral_bindings_inviter", "referral_bindings", ["inviter_id"])

    op.create_table(
        "referral_milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("binding_id", sa.Integer(), sa.ForeignKey("referral_bindings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("milestone_key", sa.String(30), nullable=False),
        sa.Column("inviter_coins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invitee_coins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inviter_battalion", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invitee_battalion", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inviter_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("granted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("binding_id", "milestone_key", name="uq_referral_milestone"),
    )

    op.create_table(
        "referral_season_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_key", sa.String(20), nullable=False),
        sa.Column("coins_earned", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("user_id", "season_key", name="uq_referral_season_stats"),
    )

    op.create_table(
        "referral_weekly_awards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_key", sa.String(12), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coins_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("awarded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("user_id", "week_key", name="uq_referral_weekly_award"),
    )


def downgrade() -> None:
    op.drop_table("referral_weekly_awards")
    op.drop_table("referral_season_stats")
    op.drop_table("referral_milestones")
    op.drop_index("ix_referral_bindings_inviter", table_name="referral_bindings")
    op.drop_table("referral_bindings")
    op.drop_index("ix_users_invite_code", table_name="users")
    op.drop_constraint("fk_users_referred_by", "users", type_="foreignkey")
    op.drop_column("users", "referred_by_user_id")
    op.drop_column("users", "invite_code")
