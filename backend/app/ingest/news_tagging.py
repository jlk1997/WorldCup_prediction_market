"""Extract team tags from news title/summary for zh/en articles."""

from __future__ import annotations

from app.data.bsd_team_names import BSD_TO_LOCAL

# English keyword (lower) -> canonical Chinese team name in DB
_EN_TO_CN: dict[str, str] = {}
for en, cn in BSD_TO_LOCAL.items():
    _EN_TO_CN[en.lower()] = cn
# Common media aliases
_EN_TO_CN.update(
    {
        "england": "英格兰",
        "france": "法国",
        "argentina": "阿根廷",
        "brazil": "巴西",
        "germany": "德国",
        "spain": "西班牙",
        "portugal": "葡萄牙",
        "netherlands": "荷兰",
        "usa": "美国",
        "u.s.a.": "美国",
        "united states": "美国",
    }
)

# Chinese football media often use these short forms
_CN_ALIASES: dict[str, str] = {
    "国足": "中国",
    "潘帕斯": "阿根廷",
    "高卢雄鸡": "法国",
    "日耳曼战车": "德国",
    "桑巴军团": "巴西",
    "三狮军团": "英格兰",
    "斗牛士": "西班牙",
}


def extract_team_tags(
    title: str,
    summary: str,
    lang: str,
    cn_team_names: list[str],
    *,
    max_tags: int = 5,
) -> list[str]:
    """Return Chinese team names (DB canonical) mentioned in the article."""
    text = f"{title or ''} {summary or ''}"
    text_lower = text.lower()
    found: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            found.append(name)

    if lang == "zh":
        for alias, canonical in _CN_ALIASES.items():
            if alias in text:
                add(canonical)
        for name in cn_team_names:
            if name in text:
                add(name)
    else:
        for en, cn in _EN_TO_CN.items():
            if en in text_lower:
                add(cn)
        for name in cn_team_names:
            if name.lower() in text_lower:
                add(name)

    return found[:max_tags]
