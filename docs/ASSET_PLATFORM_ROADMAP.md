# 足球数字资产平台路线图（Phase 0–6）

## Phase 0 — 资产基础

- 序列号、叠卡拆分、冷却期、锁定态（migration `036`–`037`）
- 实名 gate、可用积分计价、合规文案
- 核心服务：`card_asset_service`、`collectible_service`

## Phase 1 — 二级流通

- 交易行（一口价 / 竞拍）、手续费 sink
- 转赠、官方回购（积分计价）
- 行情点、Admin 经济看板

## Phase 2 — 质押与效用

- 卡牌质押产被动积分
- 竞猜 / AI 折扣等玩法赋能

## Phase 3 — 一级打新

- 首发打新、预约 / 抽签 scheduler
- 球迷币入场；人民币首发 stub（即将开放）

## Phase 4 — 数字阵容（Fantasy 基础）

- 阵容保存、赛后计分
- 成就体系、资产组合估值

## Phase 5A — Fantasy 完整闭环 ✅

- 出场分 + 星级系数
- 周榜结算（migration `038`）、周一 scheduler 发球迷币
- API：`/fantasy/me`、`/fantasy/score-log`、排行榜个人排名
- 前端：槽位交互、计分时间线、奖励说明

## Phase 5B — 卡牌对决 PVP ✅

- migration `039`：`CardDuel` / `CardDuelLog`
- 异步三卡对决、AI 模式、redeem  escrow
- 竞技场军团奖励联动、`CardDuelPanel`

## Phase 5C — 联名 / IP 发行管线 ✅

- `collab_catalog.py` + admin seed
- 收藏册「联名/IP」筛选
- Mint 页联名样式（`Collab2026`）

## Phase 5D — 卡牌-军团加成 ✅

- `card_battalion_service`：队徽 / 质押 / 传奇加成
- 助威路径应用加成；ArenaHub / 我的资产展示

## Phase 5E — 缺口修复 ✅

- 叠卡拆分文案、回购链上 recall 标记
- 合规文档同步、实名对接说明
- 经济看板调参指引

## Phase 6 — 优化与 PVP 完善 ✅

- 对决军团奖励按 duel_id 幂等（修复终身一次 bug）
- 比赛完赛即时 Fantasy 计分（live_sync + scheduler 双保险）
- 用户 vs 用户 PVP：challenge / pending / accept API + CardDuelPanel
- 全局导航：更多抽屉增加交易行/打新/阵容/资产入口
- 开发环境自动 seed 联名 catalog
- AI 计费折扣含质押卡
- 测试：battalion / collab seed / PVP / 军团幂等

## Phase 7 — Agent 资产联动与导航完善 ✅

- `AgentAssetContextService`：组合估值、持卡折扣、阵容积分、待应战对决
- AI 分析上下文注入 `user_asset`（PredictAgent prompt）
- API：`GET /api/agent/asset-context`；`billing-preview` 返回 `asset_context`
- 前端：AI 工作台资产条、持卡折扣提示；球迷中心数字资产入口；桌面导航

## Phase 8 — 安全加固与并发修复 ✅

- **PVP 卡牌锁定**：`lock_state=duel`，防止待应战时挂牌/质押/转赠
- **AI 奖池修复**：AI 模式仅单份 escrow，禁止 `stake×2` 积分增发
- **死锁预防**：accept 按 user_id 升序 `FOR UPDATE`
- **结算幂等**：已 `settled` 拒绝重复结算
- **生命周期**：挑战方取消退款、`expire_pending_pvp_duels` scheduler（默认 72h）
- **限流**：`rate_limit_card_duel` 40/min
- **质押校验**：出战前检查 active stake

## Phase 9 — 资产中心 UX 与挂牌建议 ✅

- `AssetHubService`：`GET /api/asset/hub-summary` 待办聚合（质押/对决/打新/阵容）
- `GET /api/asset/listing-hint` 地板价 + 估值 + 建议区间 + 到手预估
- 前端 `AssetHubBar`：收藏册 / 交易行 / 我的资产统一导航与徽章
- 我的资产：待办提醒条（待领质押、对决应战、进行中打新）
- 交易行：积分余额、刷新、空态 CTA、竞拍即将结束高亮
- 收藏册：挂牌弹窗集成建议价；对决锁定态文案
- 打新：人民币场次「可先参与球迷币」引导文案

## Phase 10+（未做）

- 真实 KOL 联名法务、UGC 卡面、用户公会
- 人民币打新生产接入（支付宝）
- 海外 Web3 隔离版本
- Agent 可调用资产工具（挂牌建议等，需严格权限）

## 验收清单

| 模块 | 关键验证 |
|------|----------|
| Fantasy | 完赛计分、周一发奖幂等、前端明细 |
| PVP | AI 对决 escrow、军团加分 |
| Collab | admin seed 后 Mint/收藏册可见 |
| Battalion | 助威加成与后端一致 |
| 质量 | pytest + vue-tsc 通过 |
