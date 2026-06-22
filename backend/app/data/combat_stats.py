"""卡牌对战属性 — schema、回填与传奇/队徽固定数值。"""

from __future__ import annotations

from typing import Any

STAT_KEYS = ("pace", "shoot", "pass", "dribble", "defend", "physical")

# 中文 stats 键 → 英文 combat 键
CN_STAT_MAP = {
    "速度": "pace",
    "射门": "shoot",
    "传球": "pass",
    "盘带": "dribble",
    "防守": "defend",
    "力量": "physical",
}

LEGEND_COMBAT: dict[str, dict[str, Any]] = {
    "legend_messi": {
        "position": "FWD",
        "overall_rating": 93,
        "combat_stats": {
            "pace": 85,
            "shoot": 92,
            "pass": 91,
            "dribble": 96,
            "defend": 35,
            "physical": 65,
        },
    },
    "legend_ronaldo": {
        "position": "FWD",
        "overall_rating": 92,
        "combat_stats": {
            "pace": 87,
            "shoot": 94,
            "pass": 82,
            "dribble": 88,
            "defend": 35,
            "physical": 78,
        },
    },
    "legend_neymar": {
        "position": "FWD",
        "overall_rating": 90,
        "combat_stats": {
            "pace": 91,
            "shoot": 83,
            "pass": 86,
            "dribble": 94,
            "defend": 37,
            "physical": 63,
        },
    },
}

CREST_COMBAT = {
    "position": "MID",
    "overall_rating": 78,
    "combat_stats": {
        "pace": 70,
        "shoot": 65,
        "pass": 78,
        "dribble": 72,
        "defend": 75,
        "physical": 80,
    },
}

MATCHDAY_COMBAT = {
    "position": "MID",
    "overall_rating": 82,
    "combat_stats": {
        "pace": 75,
        "shoot": 72,
        "pass": 80,
        "dribble": 78,
        "defend": 78,
        "physical": 82,
    },
}


def normalize_position(raw: str | None) -> str:
    if not raw:
        return "MID"
    u = str(raw).upper()
    if u in ("GK", "G"):
        return "GK"
    if u in ("DEF", "D", "CB", "LB", "RB", "LWB", "RWB"):
        return "DEF"
    if u in ("MID", "M", "CM", "CDM", "CAM", "LM", "RM"):
        return "MID"
    if u in ("FWD", "F", "ST", "CF", "LW", "RW"):
        return "FWD"
    return "MID"


def stats_from_player(player_stats: dict | None, overall_rating: int | None) -> dict[str, int]:
    out = {k: 50 for k in STAT_KEYS}
    if isinstance(player_stats, dict):
        for cn, en in CN_STAT_MAP.items():
            if cn in player_stats:
                out[en] = max(1, min(99, int(player_stats[cn])))
    ovr = int(overall_rating or 70)
    filled = sum(1 for k in STAT_KEYS if out[k] != 50)
    if filled < 3:
        # 无六维时用 OVR 推导合理分布
        out = {
            "pace": ovr - 5,
            "shoot": ovr,
            "pass": ovr - 3,
            "dribble": ovr - 2,
            "defend": max(30, ovr - 15),
            "physical": ovr - 8,
        }
    return {k: max(1, min(99, int(out[k]))) for k in STAT_KEYS}


def build_combat_attrs(
    *,
    card_code: str,
    series: str,
    position: str | None = None,
    overall_rating: int | None = None,
    player_stats: dict | None = None,
) -> dict[str, Any]:
    if card_code in LEGEND_COMBAT:
        base = LEGEND_COMBAT[card_code]
        return {
            "position": base["position"],
            "overall_rating": base["overall_rating"],
            "combat_stats": dict(base["combat_stats"]),
            "combat_meta": {"schema_version": 1, "source": "legend_table"},
        }
    if series == "team_crest":
        return {
            **CREST_COMBAT,
            "combat_meta": {"schema_version": 1, "source": "crest_table"},
        }
    if series == "matchday_limited":
        return {
            **MATCHDAY_COMBAT,
            "combat_meta": {"schema_version": 1, "source": "matchday_table"},
        }
    pos = normalize_position(position)
    stats = stats_from_player(player_stats, overall_rating)
    return {
        "position": pos,
        "overall_rating": int(overall_rating or 70),
        "combat_stats": stats,
        "combat_meta": {"schema_version": 1, "source": "player_sync"},
    }


def merge_combat_into_attributes(existing: dict | None, combat_block: dict[str, Any]) -> dict[str, Any]:
    attrs = dict(existing or {})
    for key in ("position", "overall_rating", "combat_stats", "combat_meta"):
        if key in combat_block:
            attrs[key] = combat_block[key]
    return attrs
