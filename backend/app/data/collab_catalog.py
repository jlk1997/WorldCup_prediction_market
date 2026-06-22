"""联名 / IP 限量卡目录（平台授权虚拟藏品，无现金价值）。"""

from __future__ import annotations

COLLAB_SERIES_CLUB = "club_collab"
COLLAB_SERIES_KOL = "kol_special"

COLLAB_CARDS: list[dict] = [
    {
        "code": "collab_messi_tribute",
        "name": "梅西 tribute · 联名纪念",
        "rarity": "legend",
        "series": COLLAB_SERIES_KOL,
        "mint_total": 999,
        "image_url": "/legends/messi-card.webp",
        "description": "平台授权虚拟联名纪念卡，限量序列号，无现金价值。",
    },
    {
        "code": "collab_brazil_crest_2026",
        "name": "巴西队徽 · 2026 联名",
        "rarity": "epic",
        "series": COLLAB_SERIES_CLUB,
        "mint_total": 500,
        "image_url": None,
        "description": "俱乐部联名系列队徽卡，可用积分二级流通。",
    },
    {
        "code": "collab_ronaldo_tribute",
        "name": "C罗 tribute · 联名纪念",
        "rarity": "legend",
        "series": COLLAB_SERIES_KOL,
        "mint_total": 888,
        "image_url": "/legends/ronaldo-card.webp",
        "description": "KOL 联名纪念系列，一级打新/二级积分流通。",
    },
]

COLLAB_SERIES_LABELS = {
    COLLAB_SERIES_CLUB: "俱乐部联名",
    COLLAB_SERIES_KOL: "KOL/IP 联名",
}
