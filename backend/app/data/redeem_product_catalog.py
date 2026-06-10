"""Bootstrap redeem shop defaults — runtime source is database products table."""

from __future__ import annotations

from app.data.redeem_grant_schema import GRANT_PAYLOAD_SCHEMA

REDEEM_PRODUCTS: list[dict] = [    {
        "sku": "redeem_frame_silver",
        "name": "银框球迷",
        "description": "300 可用积分即可兑换的入门头像框",
        "redeem_price": 300,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 5,
        "grant_payload": {"avatar_frame": "silver_wc"},
    },
    {
        "sku": "redeem_frame_gold",
        "name": "世界杯金框",
        "description": "专属头像金框，彰显世界杯球迷身份",
        "redeem_price": 400,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 10,
        "grant_payload": {"avatar_frame": "gold_wc"},
    },
    {
        "sku": "redeem_theme_spirit",
        "name": "主队 Spirit 主题",
        "description": "全站金色主题色，与主队精神共鸣",
        "redeem_price": 300,
        "per_user_limit": 1,
        "stock_total": 0,
        "sort_order": 20,
        "grant_payload": {"theme_key": "team_spirit"},
    },
    {
        "sku": "redeem_extra_free_predict",
        "name": "每日额外免费竞猜 +1",
        "description": "永久增加 1 次每日免费竞猜额度",
        "redeem_price": 600,
        "per_user_limit": 1,
        "stock_total": 200,
        "sort_order": 30,
        "grant_payload": {"extra_free_predict_daily": 1},
    },
    {
        "sku": "redeem_badge_collector",
        "name": "兑换达人徽章",
        "description": "积分商城专属荣誉徽章",
        "redeem_price": 200,
        "per_user_limit": 1,
        "stock_total": 500,
        "sort_order": 40,
        "grant_payload": {"badge_code": "redeem_collector", "badge_title": "兑换达人"},
    },
]
