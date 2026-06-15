"""029: system_ui_configs for predict reveal modal."""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "029_predict_reveal_config"
down_revision: Union[str, None] = "028_query_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_CONFIG = {
    "states": {
        "won": {
            "title": "猜中了！",
            "match_template": "{team1} vs {team2}",
            "pick_template": "{team1} vs {team2} · 你选「{pick}」",
            "show_confetti": True,
        },
        "lost": {
            "title": "差一点",
            "match_template": "{team1} vs {team2}",
            "pick_template": "{team1} vs {team2} · 你选「{pick}」",
            "show_confetti": False,
        },
        "void": {
            "title": "流局退款",
            "match_template": "{team1} vs {team2}",
            "pick_template": "{team1} vs {team2} · 你选「{pick}」",
            "show_confetti": False,
        },
    },
    "buttons": {
        "next_match": "去猜下一场",
        "share_fan_card": "分享球迷名片",
        "view_records": "查看流水",
        "dismiss": "知道了",
    },
    "hints": {
        "loss_streak_protect": "连败保护已生效：下次猜中积分有额外加成，继续加油！",
        "loss_default": "下次继续加油，下一场还有机会。",
        "void_no_score": "比赛完场超过 72 小时仍无比分，质押已原路退还。",
        "void_default": "比赛推迟或取消，质押已退还。",
    },
    "carousel": {"enabled": True, "max_items": 10, "swipe_threshold_px": 50},
    "score_template": "赛果 {score}（{result}）",
    "score_template_simple": "赛果 {score}",
}


def upgrade() -> None:
    op.create_table(
        "system_ui_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_key", sa.String(64), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("config_key", name="uq_system_ui_config_key"),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO system_ui_configs (config_key, config) VALUES (:key, CAST(:cfg AS jsonb))"),
        {"key": "predict_reveal", "cfg": json.dumps(DEFAULT_CONFIG, ensure_ascii=False)},
    )


def downgrade() -> None:
    op.drop_table("system_ui_configs")
