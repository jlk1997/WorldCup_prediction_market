-- WC2026 积分兑换商城 · 线上配置脚本
-- 执行前请备份 products / redeem_orders 表
-- 适用：PostgreSQL（与项目 Alembic 一致）
--
-- 经济模型（与后端 PREDICT_WIN_REDEEM_RATIO=0.5 对齐）：
--   免费竞猜猜中（非平局）≈ 30 累计积分 + 15 可用积分
--   5 连胜时单场可用积分可达 ~40
--   商品文案「约 N 场」按 15 可用积分/场估算
--
-- 用法：
--   psql "$DATABASE_URL" -f deploy/seed_redeem_products.sql
-- 或：
--   python backend/scripts/sync_redeem_products.py
--
-- 说明：
--   stock_total = 0 表示不限量；已售 stock_sold 不会被清零
--   ON CONFLICT 仅更新配置字段，不动 stock_sold

BEGIN;

-- 1) 上架 / 更新全部兑换商品（按 sku 幂等）
INSERT INTO products (
    sku, name, description,
    price_fen, coins_grant, grant_season_pass_days,
    product_type, pay_currency, redeem_price, grant_payload,
    per_user_limit, stock_total, stock_sold, active, sort_order, featured, updated_at
) VALUES
(
    'redeem_badge_starter',
    '初猜达人徽章',
    '入门首选 · 约猜中 7 场免费竞猜可凑够 · 展示在球迷名片',
    0, 0, 0, 'redeem', 'redeem', 100,
    '{"badge_code": "predict_starter", "badge_title": "初猜达人"}'::jsonb,
    1, 0, 0, true, 10, true, now()
),
(
    'redeem_badge_collector',
    '兑换达人徽章',
    '积分商城荣誉徽章 · 约 13 场 · 名片展示',
    0, 0, 0, 'redeem', 'redeem', 200,
    '{"badge_code": "redeem_collector", "badge_title": "兑换达人"}'::jsonb,
    1, 0, 0, true, 20, false, now()
),
(
    'redeem_theme_spirit',
    '主队 Spirit 主题',
    '全站金玫瑰主题色 · 约 19 场 · 与主队精神共鸣',
    0, 0, 0, 'redeem', 'redeem', 280,
    '{"theme_key": "team_spirit"}'::jsonb,
    1, 0, 0, true, 30, true, now()
),
(
    'redeem_frame_silver',
    '银框球迷',
    '头像银框 · 约 21 场 · 个人中心与顶栏即时生效',
    0, 0, 0, 'redeem', 'redeem', 320,
    '{"avatar_frame": "silver_wc"}'::jsonb,
    1, 0, 0, true, 40, false, now()
),
(
    'redeem_theme_gold',
    '世界杯金主题',
    '全站金色主题 · 约 25 场 · 与金框搭配更亮眼',
    0, 0, 0, 'redeem', 'redeem', 380,
    '{"theme_key": "gold_wc"}'::jsonb,
    1, 0, 0, true, 45, false, now()
),
(
    'redeem_frame_gold',
    '世界杯金框',
    '头像金框 · 约 28 场 · 排行榜与名片更醒目',
    0, 0, 0, 'redeem', 'redeem', 420,
    '{"avatar_frame": "gold_wc"}'::jsonb,
    1, 0, 0, true, 50, true, now()
),
(
    'redeem_bundle_fan',
    '球迷装扮套装',
    '银框 + Spirit 主题 · 比单买省 60 分 · 约 37 场',
    0, 0, 0, 'redeem', 'redeem', 540,
    '{"avatar_frame": "silver_wc", "theme_key": "team_spirit"}'::jsonb,
    1, 0, 0, true, 55, true, now()
),
(
    'redeem_extra_free_predict',
    '每日额外免费竞猜 +1',
    '永久 +1 次每日免费竞猜 · 约 43 场 · 长线冲榜利器',
    0, 0, 0, 'redeem', 'redeem', 650,
    '{"extra_free_predict_daily": 1}'::jsonb,
    1, 0, 0, true, 70, false, now()
)
ON CONFLICT (sku) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price_fen = 0,
    coins_grant = 0,
    grant_season_pass_days = 0,
    product_type = 'redeem',
    pay_currency = 'redeem',
    redeem_price = EXCLUDED.redeem_price,
    grant_payload = EXCLUDED.grant_payload,
    per_user_limit = EXCLUDED.per_user_limit,
    sort_order = EXCLUDED.sort_order,
    featured = EXCLUDED.featured,
    active = true,
    updated_at = now(),
    -- 不限量；若历史曾设限量且已售超出新上限，则抬高上限避免「假售罄」
    stock_total = CASE
        WHEN EXCLUDED.stock_total <= 0 THEN 0
        WHEN products.stock_sold > EXCLUDED.stock_total THEN products.stock_sold
        ELSE EXCLUDED.stock_total
    END;

-- 2) 关闭不在新目录中的旧兑换 SKU（若存在手工测试品）
UPDATE products
SET active = false, updated_at = now()
WHERE pay_currency = 'redeem'
  AND sku NOT IN (
    'redeem_badge_starter',
    'redeem_badge_collector',
    'redeem_theme_spirit',
    'redeem_frame_silver',
    'redeem_theme_gold',
    'redeem_frame_gold',
    'redeem_bundle_fan',
    'redeem_extra_free_predict'
  );

-- 3) 将「额外免费竞猜」从限量改为不限量（线上若曾设 stock_total=200）
UPDATE products
SET stock_total = 0, updated_at = now()
WHERE sku = 'redeem_extra_free_predict'
  AND stock_total > 0
  AND stock_sold < stock_total;

COMMIT;

-- 4) 验证（可选，执行后人工看一眼）
-- SELECT sku, name, redeem_price, sort_order, featured, active,
--        stock_total, stock_sold, grant_payload
-- FROM products
-- WHERE pay_currency = 'redeem'
-- ORDER BY sort_order, id;
