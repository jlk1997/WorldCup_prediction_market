"""Collection Pass (藏品赛季手册) — season config, XP curve, rewards, quests."""

from __future__ import annotations

from datetime import datetime, timezone

CURRENT_SEASON_CODE = "wc2026_s1"
MAX_LEVEL = 40

# Cumulative XP thresholds: index = level (level 1 => 0 XP required)
LEVEL_THRESHOLDS: list[int] = [0] * (MAX_LEVEL + 1)
_cum = 0
for _lv in range(2, MAX_LEVEL + 1):
    _need = 120 + (_lv - 2) * 12
    _cum += _need
    LEVEL_THRESHOLDS[_lv] = _cum

XP_SOURCES: dict[str, int] = {
    "predict_submit": 10,
    "predict_win": 25,
    "signin": 15,
    "signin_milestone": 50,
    "cheer": 5,
    "matchday_rally": 20,
    "event_cheer": 15,
    "card_drop": 15,
    "set_complete": 100,
    "quest_daily": 50,
    "quest_weekly": 150,
}

PASS_LIMITED_CARD_DEFS: list[dict] = [
    {
        "code": "pass_limited_rookie",
        "name": "手册 · 新秀徽章",
        "rarity": "rare",
        "series": "pass_limited",
        "image_url": "/legends/pass_rookie.webp",
        "attributes_json": {"tagline": "藏品赛季手册 · 新秀", "pass_level": 5},
        "is_limited": True,
        "sort_order": 9001,
    },
    {
        "code": "pass_limited_veteran",
        "name": "手册 · 老将勋章",
        "rarity": "epic",
        "series": "pass_limited",
        "image_url": "/legends/pass_veteran.webp",
        "attributes_json": {"tagline": "藏品赛季手册 · 老将", "pass_level": 20},
        "is_limited": True,
        "sort_order": 9002,
    },
    {
        "code": "pass_limited_champion",
        "name": "手册 · 冠军奖杯",
        "rarity": "legend",
        "series": "pass_limited",
        "image_url": "/legends/pass_champion.webp",
        "attributes_json": {"tagline": "藏品赛季手册 · 冠军", "pass_level": 40},
        "is_limited": True,
        "sort_order": 9003,
    },
    {
        "code": "event_limited_spotlight",
        "name": "活动 · 黑马之夜",
        "rarity": "epic",
        "series": "event_limited",
        "image_url": "/legends/event_spotlight.webp",
        "attributes_json": {"tagline": "限时活动限定", "event": "dark_horse_night"},
        "is_limited": True,
        "sort_order": 9101,
    },
    {
        "code": "event_limited_golden_boot",
        "name": "活动 · 金靴候选",
        "rarity": "epic",
        "series": "event_limited",
        "image_url": "/legends/event_golden_boot.webp",
        "attributes_json": {"tagline": "限时活动限定", "event": "golden_boot"},
        "is_limited": True,
        "sort_order": 9102,
    },
]

EVENT_SET_DEFS: list[dict] = [
    {
        "code": "event_dark_horse_set",
        "name": "黑马之夜 · 限定套",
        "description": "活动期间收集限定卡与队徽",
        "card_codes": ["event_limited_spotlight"],
        "reward_json": {
            "badge_code": "event_dark_horse",
            "badge_title": "黑马见证者",
            "fan_coins": 80,
            "redeem_points": 40,
        },
        "sort_order": 800,
    },
    {
        "code": "event_golden_boot_set",
        "name": "金靴候选 · 限定套",
        "description": "活动期间收集金靴候选限定卡",
        "card_codes": ["event_limited_golden_boot"],
        "reward_json": {
            "badge_code": "event_golden_boot",
            "badge_title": "金靴观察员",
            "fan_coins": 100,
            "redeem_points": 50,
        },
        "sort_order": 801,
    },
]

COLLECTIBLE_EVENT_DEFS: list[dict] = [
    {
        "code": "dark_horse_night",
        "name": "黑马之夜",
        "description": "活动期间应援可加权掉落限定卡",
        "starts_at": "2026-06-01 00:00:00",
        "ends_at": "2026-12-31 23:59:59",
        "event_series": "event_limited",
        "boost_json": {"forced_card_chance": 0.35, "series_weight": 3.0, "matchday_series_weight": 2.0},
        "coin_action_cost": 15,
    },
    {
        "code": "golden_boot",
        "name": "金靴候选",
        "description": "活动期间比赛日动员与应援加权掉落金靴限定卡",
        "starts_at": "2026-07-01 00:00:00",
        "ends_at": "2026-12-31 23:59:59",
        "event_series": "event_limited",
        "boost_json": {
            "forced_card_code": "event_limited_golden_boot",
            "forced_card_chance": 0.25,
            "series_weight": 4.0,
            "matchday_series_weight": 2.5,
        },
        "coin_action_cost": 20,
    },
]

DAILY_QUESTS: list[dict] = [
    {"key": "predict_once", "title": "完成 1 次竞猜", "target": 1, "xp": XP_SOURCES["quest_daily"], "action": "predict_submit"},
    {"key": "cheer_once", "title": "助威 1 次", "target": 1, "xp": XP_SOURCES["quest_daily"], "action": "cheer"},
    {"key": "signin", "title": "今日签到", "target": 1, "xp": XP_SOURCES["quest_daily"], "action": "signin"},
]

WEEKLY_QUESTS: list[dict] = [
    {"key": "predict_wins_3", "title": "本周猜中 3 场", "target": 3, "xp": XP_SOURCES["quest_weekly"], "action": "predict_win"},
    {"key": "sets_progress", "title": "完成 1 个套组", "target": 1, "xp": XP_SOURCES["quest_weekly"], "action": "set_complete"},
]

COIN_SHARD_FILL_COST: dict[str, int] = {
    "common": 2,
    "rare": 5,
    "epic": 12,
    "legend": 30,
}

XP_BOOST_COIN_COST = 30
XP_BOOST_HOURS = 24
XP_BOOST_MULTIPLIER = 1.5
DAILY_COIN_SHARD_FILL_CAP = 200


def _default_free(level: int) -> dict:
    if level % 5 == 0:
        return {"fan_coins": 15 + level // 5 * 5}
    if level % 3 == 0:
        return {"shards": {"common": 5 + level // 3}}
    return {"fan_coins": 8}


def _default_premium(level: int) -> dict:
    if level == 5:
        return {"card_code": "pass_limited_rookie"}
    if level == 20:
        return {"card_code": "pass_limited_veteran"}
    if level == 40:
        return {"card_code": "pass_limited_champion"}
    if level == 10:
        return {"avatar_frame": "pass_silver", "badge_code": "pass_lv10", "badge_title": "手册达人"}
    if level == 30:
        return {"theme_key": "pass_gold", "redeem_points": 50}
    if level % 4 == 0:
        return {"shards": {"rare": 10 + level // 4 * 2}, "redeem_points": 20}
    return {"fan_coins": 20 + level // 2}


def build_level_rewards() -> dict[int, dict]:
    rewards: dict[int, dict] = {}
    for lv in range(1, MAX_LEVEL + 1):
        rewards[lv] = {
            "free": _default_free(lv),
            "premium": _default_premium(lv),
        }
    return rewards


LEVEL_REWARDS = build_level_rewards()


def level_from_xp(xp: int) -> int:
    lv = 0
    for i in range(1, MAX_LEVEL + 1):
        if xp >= LEVEL_THRESHOLDS[i]:
            lv = i
    return lv


def xp_to_next_level(xp: int) -> tuple[int, int]:
    """Return (current_level, xp_needed_for_next)."""
    lv = level_from_xp(xp)
    if lv >= MAX_LEVEL:
        return lv, 0
    next_threshold = LEVEL_THRESHOLDS[lv + 1]
    return lv, max(0, next_threshold - xp)


def season_window() -> tuple[datetime, datetime]:
    start = datetime(2026, 6, 1, tzinfo=timezone.utc).replace(tzinfo=None)
    end = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc).replace(tzinfo=None)
    return start, end


def get_season_config() -> dict:
    start, end = season_window()
    return {
        "code": CURRENT_SEASON_CODE,
        "name": "2026 世界杯 · 藏品赛季手册",
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "max_level": MAX_LEVEL,
        "total_xp": LEVEL_THRESHOLDS[MAX_LEVEL],
        "premium_price_fen": 4500,
        "premium_sku": "collection_pass",
        "premium_plus_sku": "collection_pass_plus",
        "premium_plus_price_fen": 8800,
        "compliance_notice": (
            "藏品赛季手册为玩法进度奖励，付费仅解锁尊享轨道确定性奖励，"
            "非随机盲盒，数字藏品无金钱价值，不可交易、不可转赠、不可提现。"
        ),
    }
