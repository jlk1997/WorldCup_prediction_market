"""足球数字资产平台静态规则：稀有度估值、成就定义。"""

from __future__ import annotations

# 稀有度基准估值（可用积分）—— 用于资产组合估值、首发定价参考、行情缺省地板
RARITY_BASE_VALUE: dict[str, int] = {
    "common": 40,
    "rare": 150,
    "epic": 500,
    "legend": 2000,
}

# 星级估值系数
STAR_VALUE_MULTIPLIER: dict[int, float] = {0: 1.0, 1: 1.0, 2: 1.6, 3: 2.6}

RARITY_LABELS: dict[str, str] = {
    "common": "普通",
    "rare": "稀有",
    "epic": "史诗",
    "legend": "传奇",
}


def estimate_card_value(rarity: str, star: int = 1, *, serial_no: int | None = None, mint_total: int | None = None) -> int:
    """估算卡牌站内积分价值（非金融价值，仅作收藏/组合体验展示）。"""
    base = RARITY_BASE_VALUE.get(rarity, 40)
    mult = STAR_VALUE_MULTIPLIER.get(int(star or 1), 1.0)
    value = base * mult
    # 低序列号溢价（#1~#10 稀缺加成），仅体验向
    if serial_no and serial_no <= 10:
        value *= 1.0 + (11 - serial_no) * 0.05
    return int(round(value))


# 成就定义：code -> (名称, 描述, 检测类型, 阈值)
ACHIEVEMENTS: list[dict] = [
    {"code": "first_asset", "name": "初入藏界", "desc": "拥有第一张球星卡", "metric": "owned", "threshold": 1},
    {"code": "collector_10", "name": "小有收藏", "desc": "累计拥有 10 张球星卡", "metric": "owned", "threshold": 10},
    {"code": "collector_30", "name": "藏家", "desc": "累计拥有 30 张球星卡", "metric": "owned", "threshold": 30},
    {"code": "first_legend", "name": "传奇加冕", "desc": "拥有第一张传奇卡", "metric": "legend_owned", "threshold": 1},
    {"code": "first_trade", "name": "初试交易", "desc": "完成第一笔交易行成交", "metric": "trades", "threshold": 1},
    {"code": "trader_10", "name": "行家", "desc": "累计成交 10 笔", "metric": "trades", "threshold": 10},
    {"code": "first_stake", "name": "长期持有", "desc": "首次质押球星卡", "metric": "stakes", "threshold": 1},
    {"code": "fantasy_builder", "name": "排兵布阵", "desc": "首次组建数字阵容", "metric": "fantasy", "threshold": 1},
    {"code": "first_mint", "name": "打新先锋", "desc": "首次参与首发打新", "metric": "mints", "threshold": 1},
    {"code": "first_collab", "name": "联名藏家", "desc": "拥有第一张联名/IP 卡", "metric": "collab_owned", "threshold": 1},
    {"code": "battalion_card_master", "name": "三军徽章", "desc": "为 3 支球队持有队徽卡", "metric": "crest_teams", "threshold": 3},
    {"code": "portfolio_10k", "name": "万元身家", "desc": "资产组合估值达 10000 积分", "metric": "portfolio", "threshold": 10000},
    {"code": "ai_analyst_100", "name": "AI 百场分析师", "desc": "累计完成 100 次 AI 分析", "metric": "ai_runs", "threshold": 100},
    {"code": "series_group_collector", "name": "小组赛收藏家", "desc": "集齐小组赛系列半数以上卡牌", "metric": "series_group_pct", "threshold": 50},
]

ACHIEVEMENT_BY_CODE = {a["code"]: a for a in ACHIEVEMENTS}
