"""BSD English team names -> local Chinese DB names (48 World Cup 2026 teams)."""

from __future__ import annotations

import re

BSD_TO_LOCAL: dict[str, str] = {
    "Mexico": "墨西哥",
    "Czechia": "捷克",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Canada": "加拿大",
    "Switzerland": "瑞士",
    "Qatar": "卡塔尔",
    "Bosnia & Herzegovina": "波黑",
    "Brazil": "巴西",
    "Morocco": "摩洛哥",
    "Scotland": "苏格兰",
    "Haiti": "海地",
    "USA": "美国",
    "United States": "美国",
    "Australia": "澳大利亚",
    "Paraguay": "巴拉圭",
    "Türkiye": "土耳其",
    "Turkey": "土耳其",
    "Germany": "德国",
    "Ecuador": "厄瓜多尔",
    "Côte d'Ivoire": "科特迪瓦",
    "Ivory Coast": "科特迪瓦",
    "Curaçao": "库拉索",
    "Curacao": "库拉索",
    "Netherlands": "荷兰",
    "Japan": "日本",
    "Tunisia": "突尼斯",
    "Sweden": "瑞典",
    "Belgium": "比利时",
    "Iran": "伊朗",
    "Egypt": "埃及",
    "New Zealand": "新西兰",
    "Spain": "西班牙",
    "Uruguay": "乌拉圭",
    "Saudi Arabia": "沙特阿拉伯",
    "Cabo Verde": "佛得角",
    "France": "法国",
    "Senegal": "塞内加尔",
    "Norway": "挪威",
    "Iraq": "伊拉克",
    "Argentina": "阿根廷",
    "Austria": "奥地利",
    "Algeria": "阿尔及利亚",
    "Jordan": "约旦",
    "Portugal": "葡萄牙",
    "Colombia": "哥伦比亚",
    "Uzbekistan": "乌兹别克斯坦",
    "DR Congo": "刚果（金）",
    "Congo DR": "刚果（金）",
    "England": "英格兰",
    "Croatia": "克罗地亚",
    "Panama": "巴拿马",
    "Ghana": "加纳",
}

LOCAL_TO_BSD: dict[str, str] = {}
for eng, zh in BSD_TO_LOCAL.items():
    LOCAL_TO_BSD.setdefault(zh, eng)

_PLACEHOLDER_RE = re.compile(r"^W\d+$|^L\d+$", re.IGNORECASE)


def is_knockout_placeholder(name: str | None) -> bool:
    if not name:
        return False
    return bool(_PLACEHOLDER_RE.match(name.strip()))


def bsd_name_to_local(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip()
    if is_knockout_placeholder(name):
        return None
    return BSD_TO_LOCAL.get(name)


def local_name_to_bsd(name: str | None) -> str | None:
    if not name:
        return None
    return LOCAL_TO_BSD.get(name.strip())


def normalize_group_label(group_name: str | None) -> str | None:
    """Map local 'A组' or BSD 'Group A' to 'Group A'."""
    if not group_name:
        return None
    g = group_name.strip()
    if g.startswith("Group "):
        return g
    m = re.match(r"^([A-L])组", g)
    if m:
        return f"Group {m.group(1)}"
    m = re.search(r"Group\s+([A-L])", g, re.IGNORECASE)
    if m:
        return f"Group {m.group(1).upper()}"
    return None
