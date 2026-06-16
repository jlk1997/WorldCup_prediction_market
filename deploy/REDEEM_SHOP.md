# 积分兑换商城配置说明

与充值商城（`pay_currency=cash`）分离；用户用 **可用积分**（`users.redeem_points`）兑换，**不扣累计积分**。

## 经济模型

| 概念 | 来源 | 用途 |
|------|------|------|
| 累计积分 | 猜中、召友荣誉等 | 冲榜排名，兑换不消耗 |
| 可用积分 | 仅竞猜猜中获得（≈ 累计的 50%，见 `PREDICT_WIN_REDEEM_RATIO`） | 积分商城消费 |

单场免费竞猜猜中（非平局）典型收益：

- 累计积分 ≈ **30**（含连胜加成可更高）
- 可用积分 ≈ **15**（比例 0.5 时）

商品描述里的「约 N 场」按 **15 可用积分/场** 估算，方便用户心算目标。

## 商品阶梯（2026 世界杯赛季）

| 排序 | SKU | 名称 | 积分 | 推荐 | 权益 |
|------|-----|------|------|------|------|
| 10 | redeem_badge_starter | 初猜达人徽章 | 100 | ✅ | 名片徽章 |
| 20 | redeem_badge_collector | 兑换达人徽章 | 200 | | 名片徽章 |
| 30 | redeem_theme_spirit | 主队 Spirit 主题 | 280 | ✅ | 全站主题 |
| 40 | redeem_frame_silver | 银框球迷 | 320 | | 头像银框 |
| 45 | redeem_theme_gold | 世界杯金主题 | 380 | | 全站金主题 |
| 50 | redeem_frame_gold | 世界杯金框 | 420 | ✅ | 头像金框 |
| 55 | redeem_bundle_fan | 球迷装扮套装 | 540 | ✅ | 银框+Spirit（比单买省 60） |
| 70 | redeem_extra_free_predict | 每日额外免费竞猜 +1 | 650 | | 永久 +1 免费猜/日 |

设计原则：

1. **100 分入门徽章** — 约 7 场即可兑换，给新用户第一个可见目标（配合个人中心「还差 X 分换 XX」进度条）。
2. **装扮分层** — 主题 → 银框 → 金主题 → 金框，价格递进；套装给「省心价」。
3. **权益类放最后** — 额外免费猜影响留存与平衡，定价最高；**不限量**（`stock_total=0`），避免世界杯期间「假稀缺」挫败。
4. **与现金装扮区分** — ¥12「主队装扮包」仍走支付宝；积分路径更慢但零付费，适合活跃球迷。

## 线上更新

### 方式 A：SQL（推荐生产一次性对齐）

```bash
psql "$DATABASE_URL" -f deploy/seed_redeem_products.sql
```

脚本特点：按 `sku` 幂等 UPSERT；**不重置** `stock_sold`；自动下架不在目录内的测试 SKU。

### 方式 B：代码同步

```bash
cd backend
python scripts/sync_redeem_products.py
# 可选：下架代码里已删除的 SKU
python scripts/sync_redeem_products.py --deactivate-missing
```

源码目录：`backend/app/data/redeem_product_catalog.py`

### 验证

```bash
curl -s https://loveaibaby.cn/api/shop/redeem/rules | jq '.products[] | {sku, redeem_price, name}'
```

或登录后打开 `/shop?tab=redeem` 查看「积分兑换」Tab。

## 管理 API

需 `X-Admin-Secret`，详见 `backend/app/api/routes/commerce.py` 中 redeem admin 路由。临时调价可改 DB 后清缓存（如有）；长期以 catalog + SQL 为准。

## 与增长规划的关系

- 每日任务完成后的 **兑换进度条**（`redeem_progress`）按 **最低价在架商品** 计算差距。
- 排行榜赛季虚拟奖可发 **可用积分**，与商城商品联动。
- 运营话术：「猜中拿可用积分 → 商城换头像框/主题 → 名片晒给球友」。
