# AI + 足球 NFT 生态 — 长期设计与落地状态

> 产品规划详见 Cursor Plan「AI足球NFT生态规划」；本文档记录 **工程落地状态** 与 **下一阶段设计**，不替代合规文档。

## 1. 北极星与飞轮（已对齐）

- **日活轮**：Live → 竞猜 → AI → 排行榜/军团
- **资产轮**：掉卡 → 打新 → 对决/Fantasy/质押 → 积分二级
- **变现**：球迷币/AI/通行证 + RMB 打新 + 手册尊享

## 2. Phase 11–15 工程状态

| 阶段 | 能力 | 状态 |
|------|------|------|
| 11 | PredictHall AI 摘要 + 跟 AI 选 + 结算桥接 | ✅ |
| 11 | 今日主场 + 移动 AI Tab + Onboarding 9 步 | ✅ |
| 11 | 生产 checklist + whitelist 脚本 | ✅ |
| 12 | AI 教练（组牌/ Fantasy/ 打新顾问）+ AI 包 SKU | ✅ |
| 12 | 知识库注入 DataAgent | ✅ `prediction_knowledge_service` |
| 12 | 挂牌顾问 ai_note | ✅ |
| 13 | 比赛日编排 + AI 推送 | ✅ scheduler |
| 13 | Live 卡片竞猜/AI/Insight | ✅ |
| 13 | 分享海报 + Admin 四合一监控 | ✅ |
| 14 | 赛季三幕叙事 API + UI | ✅ |
| 14 | 军团 2.0 房间目标 | ✅ |
| 14 | 支付宝原路退款 + 积分赛季文档 | ✅ |
| 15 | 反作弊限频 + Widget + 产品埋点表 | ✅ |

## 3. 数据与观测

- **前端**：`trackEvent` → Umami/百度 + 关键事件 POST `/api/analytics/event`
- **Admin**：`/api/asset/admin/ops-dashboard` — 订单/链/AI 队列/漏斗事件
- **建议 North Star SQL**（示意）：WAU 中 `predict_submit` 且（`mint_order_paid` OR `ai_analysis_complete` OR 资产互动）占比

## 4. 下一阶段设计（Post Phase 15）

### 4.1 商业化

- `mint_bundle` 与具体打新活动 **SKU 绑定**（Admin `/admin/economy` 绑定 UI + `POST bind-mint`）✅
- 赛季礼包 `season_ultimate`（通行证+手册+框）✅ migration `046`
- 比赛日复购 push + 限量卡 narrative A/B ✅ `matchday_repurchase` + 今日主场入口

### 4.2 AI

- 结算页 **AI pick vs 用户 pick** 对比条 ✅
- Fantasy 周报通知（站内）✅ scheduler 周一结算后推送
- 知识库按淘汰赛阶段 **自动切换 excerpt** ✅ `round_type` / `bracket_round`

### 4.3 链与合规

- 链铸造失败 **埋点 + Admin 告警阈值** ✅ `chain_mint_failed` / ops `chain.alert`
- 分享页固定免责声明模板（已实现 SharePosterSheet）

### 4.4 规模化

- Redis 必选 + AI 队列可视化告警阈值 ✅ `check_production_readiness` + ops `ai.alert`
- Live ingest 与 API 进程分离（部署文档）✅ `docs/DEPLOY_SCALE.md`
- 设备指纹（反作弊 v2）✅ `X-Device-Id` + Redis 限频

### 4.5 体验与 UI/UX（Post Phase 15+）

- 链铸造失败 **一键重试横幅** ✅ `ChainAlertBanner`（今日主场/收藏册）
- 比赛日/Fantasy **增长通知** ✅ 顶栏 `MatchdayGrowthNotifier`
- 竞猜 AI 条 **置信度 + 胜率条 + 跟选反馈** ✅ `PredictMatchAiStrip`
- 赛季终极礼包 **商城 Hero** ✅ `Shop.vue`
- 打新 **比赛日高亮 + deep link 滚动** ✅ `MintEvent.vue`
- 竞猜大厅嵌入 **今日主场** ✅ `PredictHall`
- 移动端 **比赛日 Tab 角标** ✅ `MobileBottomNav`
- API 冒烟脚本 ✅ `scripts/e2e_smoke_checklist.py`
- 竞猜结算 **猜中晒海报** ✅ `PredictSettlementReveal` → `openPredictShareSheet`
- 交易行挂牌详情 **AI 顾问提示** ✅ `Marketplace.vue` + `listing_detail.ai_note`

### 4.6 可靠性与幂等（Post Phase 15+）

- 支付履约 **`grant_result_json` 闸门** ✅ 已付订单重试 notify/sync 时补发未完成的 grant
- `mint_bundle` **重复 grant 防护** ✅ 订单级幂等 + `MintReservation` 行锁 / 唯一约束回退
- Fantasy 周榜结算 **先落 settlement 再发币** ✅ `with_for_update` + `begin_nested` 防双发
- 链铸造埋点 **不提前 commit** ✅ `ProductAnalyticsService.track(commit=False)` 与外层事务一致

### 4.7 性能与响应速度（Post Phase 15+）

- 今日主场 **Redis 短缓存**（15s/用户）+ 全局 live mints 缓存 ✅ `TodayHomeService`
- Hub 轻量聚合 **跳过组合估值/全量成就列表** ✅ `AssetHubService.hub_summary(light=True)`
- 日常状态 **15s 缓存** + 竞猜/签到后失效 ✅ `user_surface_cache`
- 商城商品列表 / 交易行卡牌行情 **短 TTL 缓存** ✅ `/api/shop/products`、`card_market_data`
- API **GZip 压缩**（>800B）✅ `GZipMiddleware`
- 前端今日主场 **共享 store**（20s）并回填 `dailyStatus` ✅ `todayHomeStore`

### 4.8 文昌链 / NFT（Post Phase 15+）

- 掉卡/打新 **异步 queue → AVATA 铸造** ✅ `CollectibleChainService`
- 历史卡 **backfill** ✅ `scripts/backfill_chain_mint.py`
- 链账户轮询 + pending 超时 ✅ `_poll_account_creation` / `mint_timeout`
- **溯源 API** ✅ `/user-card/{id}/provenance`
- 全链路 UI：收藏册/支付结果/订单/交易行 ✅
- 诊断/E2E ✅ `diagnose_chain_status.py` / `e2e_chain_checklist.py`

## 5. 配置速查

| 变量 | 用途 |
|------|------|
| `PREDICTION_KNOWLEDGE_ENABLED` | 注入 WC2026 知识库 |
| `PREDICTION_KNOWLEDGE_PATH` | 知识库 md 路径 |
| `AGENT_ENABLE_TOOL_LOOP_ADVISE` | 登录用户分析启用资产 tool loop |
| `ASSET_AI_CARD_DISCOUNT_PCT` | 持卡 AI 折扣 |
| `AI_QUEUE_ALERT_PCT` | Ops 大盘 AI 队列利用率告警阈值（默认 85） |
| `REDIS_URL` | 生产必选：限频、AI 槽位、分布式锁 |

## 6. 验收清单（运营）

1. 新用户：Onboarding 9 步 → 首猜 → PredictHall 看到 AI → 猜中掉卡桥接
2. 比赛日：主队收到 `matchday_ai` 通知 → Live/竞猜/AI 一致
3. RMB：`check_production_readiness.py` PASS → 真实 E2E 打新
4. Admin：ops 大盘订单成功率、链 pending、漏斗事件可查
