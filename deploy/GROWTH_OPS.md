# WC2026 冷启动运营手册（增长 / 留存 / 付费）

与 [SEO_WEBMASTER.md](./SEO_WEBMASTER.md)、[SEO_CONTENT_OUTREACH.md](./SEO_CONTENT_OUTREACH.md) 并行执行。SEO 负责「被发现」，本文负责「玩起来、留下来、付钱、拉人」。

## 一、种子用户（30–50 人）

**目标：** 走完「注册 → 建档 → 首猜 → 发邀请码」完整漏斗，产生第一批有效邀请。

| 步骤 | 动作 |
|------|------|
| 1 | 从朋友 / 球迷群邀请 30–50 人，每人给专属邀请码 |
| 2 | 引导完成 4 步建档（必选主队） |
| 3 | 当场完成 1 次免费竞猜（Tour 结束会跳转 `/predict`） |
| 4 | 提交后复制「我押了 X 队」文案，发到群里 |
| 5 | 记录每人是否 24h 内完成首猜 |

**有效邀请定义：** 好友注册 + 完成档案 + 至少 1 次首玩（与产品内召友规则一致）。

## 二、比赛日节奏（QQ 群 / 社群）

**原则：** 链接直达行动页，不要只发首页。

| 时间点 | 群发内容 |
|--------|----------|
| 开赛前 2h | 「今日 X vs Y 开猜了」+ `https://loveaibaby.cn/predict?highlight=场次ID` |
| 开赛前 30min | 「Live 比分」+ `https://loveaibaby.cn/live` |
| 赛后 30min | 「待开奖提醒 · 去个人中心看结果」+ `https://loveaibaby.cn/me?focus=predictions` |
| 非比赛日 | 签到 + 问答任务 + `https://loveaibaby.cn/me` |

**QQ 群福利：** 产品内「加入官方 QQ 群领 50 币」链接固定放在群公告；比赛日强调签到 +10 币加成。

## 三、每周漏斗复盘

每 **周一** 对照以下指标（百度统计 + 自建埋点 `trackEvent`）：

| 漏斗阶段 | 埋点 / 数据来源 | 4 周目标 |
|----------|-----------------|----------|
| 注册 | 后端 users 表 | 基线 + 种子 |
| 24h 内首猜 | `first_predict_submit` | >40% |
| 建档完成 | `onboarding_complete` + profile_completed | >65% |
| D7 留存 | 登录日志 / 百度统计 | >15% |
| 付费 | 订单表 paid | >2% 注册用户 |
| 有效邀请 / 注册 | referral effective_invites | >0.15 |

**复盘模板（复制到周会）：**

```
本周：注册 __ / 首猜 __% / 建档 __% / D7 __% / 付费 __ / 有效邀请 __
比赛日 DAU __ vs 非比赛日 __（比 __）
Top 问题：__
下周动作：__
```

**管理员漏斗 API**（需请求头 `X-Admin-Secret`）：

```bash
curl -H "X-Admin-Secret: YOUR_SECRET" "https://loveaibaby.cn/api/game/admin/funnel-summary?days=7"
```

**赛季榜虚拟奖结算**（世界杯结束后执行一次）：

```bash
curl -X POST -H "X-Admin-Secret: YOUR_SECRET" \
  "https://loveaibaby.cn/api/game/admin/leaderboard/settle-season?board=points"
```

## 四、产品内已落地的增长触点（供运营对齐话术）

- **新用户 Tour（6 步）** → 结束跳转竞猜大厅
- **建档完成** → 主按钮「去猜主队下一场」
- **首页 / Live / 赛程表** → 「去竞猜」按钮
- **猜中滚动 feed** → 点击跳转竞猜大厅（社交证明）
- **提交竞猜后** → 可复制「我押了 X 队」+ `/share/match/{id}` 邀友链接
- **每日任务完成后** → 第二曲线：连胜守护 / 兑换进度 / 冲榜差距 / 通行证日领 / 召友
- **冲榜弹窗** → 文案已对齐「站内虚拟奖励」，不含实物承诺
- **浏览器通知 MVP** → 用户授权后可收待开奖 / 连胜提醒（需 HTTPS）
- **6 元小包推荐** → 质押或 AI 币不足时弹窗推荐 `coins_small`
- **通行证价值条** → 竞猜页 / 商城显示「今日已省 X 币」
- **官方 QQ 群条** → 未领群福利时首页 / 竞猜页展示
- **登录后默认** → 建档完成用户登录后跳转 `/predict`；本会话首次进首页且未竞猜也会导向竞猜页
- **GrowthPrimaryCard** → 合并首猜/第二猜/推荐场次为一张主行动卡，减少横幅堆叠
- **激活分群引擎** → `daily-status` 返回 `activation_segment` / `duel_segment` / `card_nudge` / `primary_pillar`
- **SecondPredictCoach** → 首猜成功 / 猜错关闭后底部引导（全局挂载）
- **MatchDayShareBar** → 比赛日一键复制 `?ref=&highlight=` 深链
- **手机底栏** → 未首猜时「竞猜」Tab 显示「猜」提示点
- **召友中心** → 比赛日显示 MatchDayShareBar 一键复制深链
- **AI 先猜门槛** → 未首猜时导航 / 首页 AI 按钮显示「先猜」；AI 工作台软引导
- **增长埋点** → `activation_recovery_*` / `comeback_banner_*` / `second_predict_coach_*` 供周报复盘
- **竞猜教练聚光灯** → 首次进竞猜页逐步高亮选胜负 / 免费 / 提交
- **提交后分享海报** → PredictShareSheet 文案 + 新版球场风海报（三步引导 + 白底二维码）
- **开赛前 2h 提醒** → 浏览器通知（需用户授权 + HTTPS）
- **通行证一键领币** → 竞猜页 PassDailyClaimBar
- **兑换估算** → 「约再猜中 N 场可换装扮」
- **积分商城阶梯** → 见 [REDEEM_SHOP.md](./REDEEM_SHOP.md) · 线上执行 `deploy/seed_redeem_products.sql`
- **主榜虚拟奖结算** → 赛后管理员 `POST /api/game/admin/leaderboard/settle-season` 发放站内币/积分
- **QQ 群签到人数** → 首页/竞猜页展示「今日已有 X 位球友签到」
- **猜中 feed 条（WinFeedBar）** → 首页/竞猜页展示「刚刚 N 人猜中」+ 绿点动画 +「我也去猜」；首页手机端悬浮在底部导航上方
- **连胜守护条（StreakRiskBanner）** → 首页/竞猜页顶部，点击直达推荐场次
- **未登录引导（GuestLoginBanner）** → 竞猜页 / Live「我的球队」Tab 引导登录免费猜
- **猜中弹窗** → 主按钮优先「保连胜 / 猜下一场」；「晒预测 · 海报」打开全局分享弹窗（含微信保存提示）
- **排行榜差距 CTA** → 差 X 分超上一名时显示「去竞猜赚积分 / 邀友冲榜」
- **分享海报三步指引** → 邀友弹窗 + 提交后 PredictShareSheet 均提示「微信里先保存海报再长按发群」

## 五、激活分群与深链（2026-06 诊断落地）

基于 [GROWTH_ANALYSIS_REPORT.md](./GROWTH_ANALYSIS_REPORT.md) 的 48 用户诊断，产品内已按 **activation_segment** 分群推送：

| 分群 | 含义 | 产品触点 | 运营话术 |
|------|------|----------|----------|
| `never_predicted` | 注册但未猜 | 首页/竞猜页 **ActivationRecoveryBar** · 首次进首页跳 `/predict` | 「免费猜一场 · 30 秒 · 猜中得积分」 |
| `profile_only` | 已建档未猜 | 同上，文案强调「档案已就绪」 | 「你已选主队，还差一步完成首猜」 |
| `one_and_done` | 只猜过 1 次 | **SecondPredictCoach** · 每日 next_action 推第二猜 | 「再猜一场 · 离换徽章更近」 |
| `active` | 猜≥2 次或对决≥3 场 | 常规每日任务 / 连胜 / 兑换进度 | 维持习惯与比赛日动员 |

**对决分群 `duel_segment`（双轴激活）：**

| 分群 | 含义 | 产品触点 |
|------|------|----------|
| `never_dueled` | 有卡未对决 | 卡牌中心 **CardHubHero** 快速匹配 · **GrowthPrimaryCard** |
| `one_duel` | 对决 1 场 | 同上 + 手册对决任务 |
| `duel_active` | 对决≥3 场 | 排位赛季榜 · 凭证战队列 |

**增长埋点（对决）：** `duel_match_enter` · `duel_complete` · `duel_fee_sink` · `weekly_card_hub_visit`（页面埋点）

**深链参数：**

- `https://loveaibaby.cn/predict?highlight={matchId}` — 直达场次卡片
- `https://loveaibaby.cn/predict?ref={invite_code}&highlight={matchId}` — 比赛日裂变（首页 **MatchDayShareBar** 一键复制）
- 未首猜用户进 **AI 工作台** → 软引导先去竞猜（不封禁）

**2 周验收目标（复盘时对照）：**

| 指标 | 诊断基线 | 目标 |
|------|----------|------|
| 猜≥2 次用户占比 | 6%（3/48） | **20%** |
| ever 签到占比 | 29% | **40%** |
| 比赛日 DAU | — | **≥15** |

**复盘 SQL：** 复用 [analyze_growth_readonly.sql](./analyze_growth_readonly.sql) 第 3、4 组；或本地 `python backend/scripts/analyze_growth.py`（只读，勿提交含邮箱的 JSON）。

## 六、收录与 SEO（并行，不替代产品漏斗）

- Google Search Console：每周看索引量、点击、CTR
- 百度：`site:loveaibaby.cn` 抽查收录
- 外链按计划发知乎 / 小红书软文（见 SEO_CONTENT_OUTREACH.md）

## 七、不建议现在做

- 买量投放（漏斗数据不足）
- 复杂好友 Feed / 私信
- 微信 JSSDK 分享（成本高，继续 OG + 海报）
- 自动检测 QQ 入群（无 API）

---

**负责人分工建议：** 开发维护产品与埋点；运营负责种子、比赛日群节奏、每周复盘表；站长维护 sitemap / 收录。
