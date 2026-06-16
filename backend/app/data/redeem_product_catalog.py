"""Bootstrap redeem shop defaults — runtime source is database products table.

Economy reference (PREDICT_WIN_REDEEM_RATIO=0.5):
  - Free predict win (non-draw): ~30 累计积分 → ~15 可用积分
  - With 5-win streak: up to ~80 / ~40
  - Prices below assume ~15 可用积分 per free win for copywriting only.
"""

from __future__ import annotations

from app.data.redeem_grant_schema import GRANT_PAYLOAD_SCHEMA

# stock_total=0 → unlimited; per_user_limit=0 → no per-user cap
REDEEM_PRODUCTS: list[dict] = [
    {
        "sku": "redeem_badge_starter",
        "name": "初猜达人徽章",
        "description": "入门首选 · 约猜中 7 场免费竞猜可凑够 · 展示在球迷名片",
        "redeem_price": 100,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 10,
        "featured": True,
        "grant_payload": {"badge_code": "predict_starter", "badge_title": "初猜达人"},
    },
    {
        "sku": "redeem_badge_collector",
        "name": "兑换达人徽章",
        "description": "积分商城荣誉徽章 · 约 13 场 · 名片展示",
        "redeem_price": 200,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 20,
        "featured": False,
        "grant_payload": {"badge_code": "redeem_collector", "badge_title": "兑换达人"},
    },
    {
        "sku": "redeem_theme_spirit",
        "name": "主队 Spirit 主题",
        "description": "全站金玫瑰主题色 · 约 19 场 · 与主队精神共鸣",
        "redeem_price": 280,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 30,
        "featured": True,
        "grant_payload": {"theme_key": "team_spirit"},
    },
    {
        "sku": "redeem_frame_silver",
        "name": "银框球迷",
        "description": "头像银框 · 约 21 场 · 个人中心与顶栏即时生效",
        "redeem_price": 320,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 40,
        "featured": False,
        "grant_payload": {"avatar_frame": "silver_wc"},
    },
    {
        "sku": "redeem_theme_gold",
        "name": "世界杯金主题",
        "description": "全站金色主题 · 约 25 场 · 与金框搭配更亮眼",
        "redeem_price": 380,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 45,
        "featured": False,
        "grant_payload": {"theme_key": "gold_wc"},
    },
    {
        "sku": "redeem_frame_gold",
        "name": "世界杯金框",
        "description": "头像金框 · 约 28 场 · 排行榜与名片更醒目",
        "redeem_price": 420,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 50,
        "featured": True,
        "grant_payload": {"avatar_frame": "gold_wc"},
    },
    {
        "sku": "redeem_bundle_fan",
        "name": "球迷装扮套装",
        "description": "银框 + Spirit 主题 · 比单买省 60 分 · 约 37 场",
        "redeem_price": 540,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 55,
        "featured": True,
        "grant_payload": {"avatar_frame": "silver_wc", "theme_key": "team_spirit"},
    },
    {
        "sku": "redeem_extra_free_predict",
        "name": "每日额外免费竞猜 +1",
        "description": "永久 +1 次每日免费竞猜 · 约 43 场 · 长线冲榜利器",
        "redeem_price": 650,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 70,
        "featured": False,
        "grant_payload": {"extra_free_predict_daily": 1},
    },
]
