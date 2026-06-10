"""Football relevance filter for RSS ingest and news listing."""

from __future__ import annotations

import re

# 明显非足球项目 — 命中则直接丢弃
_EXCLUDE_ZH = (
    "篮球",
    "nba",
    "cba",
    "排球",
    "网球",
    "羽毛球",
    "乒乓球",
    "游泳",
    "田径",
    "马拉松",
    "滑雪",
    "冰球",
    "高尔夫",
    "拳击",
    "格斗",
    "ufc",
    "f1",
    "赛车",
    "举重",
    "体操",
    "跳水",
    "自行车",
    "攀岩",
    "斯诺克",
    "棒球",
    "mlb",
    "橄榄球",
    "曲棍球",
    "手球",
    "射击",
    "射箭",
    "柔道",
    "跆拳道",
    "摔跤",
    "赛艇",
    "帆船",
    "马术",
    "铁人三项",
    "残运会",
    "冬奥会",
    "夏奥",
)

_EXCLUDE_EN = (
    "basketball",
    "nba",
    "volleyball",
    "tennis",
    "badminton",
    "table tennis",
    "swimming",
    "athletics",
    "marathon",
    "skiing",
    "hockey",
    "golf",
    "boxing",
    "ufc",
    "mma",
    "formula 1",
    " f1 ",
    "motorsport",
    "cricket",
    "rugby",
    "baseball",
    "mlb",
    "snooker",
    "cycling",
    "gymnastics",
    "diving",
    "weightlifting",
    "esports",
    " e-sport",
)

# 足球 / 世界杯相关 — 命中其一视为相关
_INCLUDE_ZH = (
    "足球",
    "世界杯",
    "世预赛",
    "世俱杯",
    "欧冠",
    "欧联",
    "亚冠",
    "中超",
    "英超",
    "西甲",
    "德甲",
    "意甲",
    "法甲",
    "国足",
    "女足",
    "门将",
    "进球",
    "射门",
    "点球",
    "红牌",
    "黄牌",
    "转会",
    "主帅",
    "教练",
    "足协",
    "fifa",
    "友谊赛",
    "淘汰赛",
    "小组赛",
    "决赛",
    "半决赛",
    "加时",
    "德比",
    "梅西",
    "c罗",
    "姆巴佩",
    "哈兰德",
    "利物浦",
    "皇马",
    "巴萨",
    "曼联",
    "曼城",
    "阿森纳",
    "切尔西",
    "拜仁",
    "多特",
    "尤文",
    "米兰",
    "巴黎圣日耳曼",
    "潘帕斯",
    "三狮",
    "高卢",
    "桑巴",
    "日耳曼战车",
    "斗牛士",
)

_INCLUDE_EN = (
    "football",
    "soccer",
    "world cup",
    "fifa",
    "uefa",
    "champions league",
    "europa league",
    "premier league",
    "la liga",
    "bundesliga",
    "serie a",
    "ligue 1",
    "goal",
    "penalty",
    "striker",
    "midfielder",
    "defender",
    "goalkeeper",
    "transfer",
    "manager",
    "coach",
    "fixture",
    "knockout",
    "group stage",
    "semi-final",
    "quarter-final",
    "var ",
    "offside",
    "clean sheet",
    "hat-trick",
)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    for kw in keywords:
        if " " in kw or len(kw) <= 3:
            if kw in text:
                return True
        elif kw in text:
            return True
    return False


def is_football_relevant(
    title: str,
    summary: str,
    lang: str,
    *,
    team_tags: list[str] | None = None,
) -> bool:
    """Return True if the article is football-related enough to show."""
    text = f"{title or ''} {summary or ''}".strip()
    if not text:
        return False

    text_lower = text.lower()
    text_norm = re.sub(r"\s+", " ", text_lower)

    if lang == "zh":
        if _contains_any(text_lower, _EXCLUDE_ZH):
            return False
        if team_tags:
            return True
        return _contains_any(text_lower, _INCLUDE_ZH) or _contains_any(text, _INCLUDE_ZH)

    if _contains_any(text_norm, _EXCLUDE_EN):
        return False
    if team_tags:
        return True
    return _contains_any(text_norm, _INCLUDE_EN)
