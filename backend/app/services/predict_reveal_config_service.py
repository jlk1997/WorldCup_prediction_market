"""DB-backed configuration for predict settlement reveal modal."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.commerce import SystemUiConfig

CONFIG_KEY = "predict_reveal"

DEFAULT_PREDICT_REVEAL_CONFIG: dict = {
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
    "carousel": {
        "enabled": True,
        "max_items": 10,
        "swipe_threshold_px": 50,
    },
    "score_template": "赛果 {score}（{result}）",
    "score_template_simple": "赛果 {score}",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


class PredictRevealConfigService:
    def __init__(self, db: Session):
        self.db = db

    def get_config(self) -> dict:
        row = self.db.query(SystemUiConfig).filter(SystemUiConfig.config_key == CONFIG_KEY).first()
        if not row or not row.config:
            return deepcopy(DEFAULT_PREDICT_REVEAL_CONFIG)
        return _deep_merge(DEFAULT_PREDICT_REVEAL_CONFIG, row.config)

    def upsert_config(self, patch: dict) -> dict:
        row = self.db.query(SystemUiConfig).filter(SystemUiConfig.config_key == CONFIG_KEY).first()
        merged = _deep_merge(self.get_config(), patch)
        if row:
            row.config = merged
            row.updated_at = _utcnow()
        else:
            row = SystemUiConfig(config_key=CONFIG_KEY, config=merged)
            self.db.add(row)
        self.db.flush()
        return merged
