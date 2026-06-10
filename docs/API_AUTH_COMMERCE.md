# 用户与商业化 API

## Auth

| Method | Path | Auth | Body |
|--------|------|------|------|
| POST | `/api/auth/send-code` | - | `{ "email", "age_confirmed": true }` |
| POST | `/api/auth/verify` | - | `{ "email", "code", "age_confirmed": true }` → tokens + user |
| POST | `/api/auth/refresh` | - | `{ "refresh_token" }` |
| GET | `/api/auth/me` | Bearer | 当前用户 |
| PATCH | `/api/auth/me` | Bearer | `{ nickname?, favorite_team_id? }` 改昵称扣 20 币 |

## Profile / Onboarding

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/profile/status` | Bearer | 档案完成态、主/副队、球星、missing_steps |
| GET | `/api/profile/teams` | - | 48 队轻量列表（缓存 10min） |
| GET | `/api/profile/players` | - | `?team_ids=1,2` 主/副队 roster |
| PUT | `/api/profile/setup` | Bearer | 一次性提交 `{ main_team_id, secondary_team_id?, player_ids[1-3] }` |
| PATCH | `/api/profile` | Bearer | 后续修改偏好 |
| GET | `/api/profile/recommendations` | opt | 主队下一场、CTA、fan_identity |

## Game

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/game/matches` | opt | 可竞猜比赛（登录后含 is_main_team/can_cheer 等） |
| POST | `/api/game/predict` | Bearer | 提交竞猜（质押需 profile_completed） |
| GET | `/api/game/my-predictions` | Bearer | 我的记录 |
| POST | `/api/game/signin` | Bearer | 每日签到（比赛日 +10 加成） |
| GET | `/api/game/leaderboard` | - | `?period=daily\|weekly\|season` |
| GET | `/api/game/fan-rank` | - | 主队粉丝榜 |
| GET | `/api/game/team-contribution` | - | `?team_id=` 主队贡献榜 |
| POST | `/api/game/cheer` | Bearer | `{ match_id, team_id }` 5 币助威 |
| GET | `/api/game/cheer/{match_id}` | opt | 双方助威条 + 是否已助威 |
| GET | `/api/game/quiz/today` | Bearer | 今日题目 |
| POST | `/api/game/quiz/answer` | Bearer | `{ answer_index }` 每日 1 次 |
| GET | `/api/game/fan-card` | Bearer | 球迷名片数据 |

## Arena（军团擂台）

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/arena/overview` | Bearer | 个人站况 + 下一场擂台 + 球星摘要 |
| GET | `/api/arena/team-rank` | - | `?team_id=&period=daily\|weekly\|season` 军团榜 |
| GET | `/api/arena/match/{match_id}` | opt | 双队擂台战力 |
| GET | `/api/arena/star-heat` | opt | `?scope=my\|global` 球星热力 |
| GET | `/api/arena/star-accuracy` | - | 球星竞猜准确率榜 |
| GET | `/api/arena/matchday-goal` | Bearer | 比赛日动员进度 |
| POST | `/api/arena/boost/star` | Bearer | `{ player_id }` 球星应援 3 币 |
| POST | `/api/arena/boost/cheer-extra` | Bearer | `{ match_id }` 助威加码 10 币 |
| POST | `/api/arena/boost/matchday-rally` | Bearer | 比赛日动员 20 币 |

## Shop & Pay

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/shop/products` | - |
| POST | `/api/pay/alipay/create` | Bearer | `{ product_id, age_confirmed: true }` |
| POST | `/api/pay/alipay/notify` | 支付宝 |
| GET | `/api/pay/orders` | Bearer | 我的订单列表 |
| GET | `/api/pay/orders/{id}` | Bearer |

## Wallet

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/wallet/ledger` | Bearer | `?limit=50` 球迷币流水 |

## AI Agent

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/agent/billing-status` | Bearer | 免费额度、扣币价格、余额 |
| POST | `/api/agent/billing-preview` | Bearer | 本次分析预计扣费（含 cache_hit） |
| POST | `/api/agent/analyze` | Bearer | 触发分析（cache miss 扣额度/币） |
| POST | `/api/agent/analyze/stream` | Bearer | SSE 流式分析 |
| GET | `/api/agent/insight` | opt | 只读缓存摘要，不触发 LLM |
| POST | `/api/agent/insights/batch` | opt | 批量读缓存 |
| GET | `/api/agent/runs` | Bearer | 仅本人历史 run |
| GET | `/api/agent/runs/{id}` | Bearer | 本人或公共 cache 摘要 |

`POST /api/predict/analysis` 已废弃（410），请改用 `/api/agent/analyze`。

分析响应可选字段 `billing`：`charge_coins`、`used_free_quota`、`free_remaining` 等。

## 前端路由

| 路径 | 说明 |
|------|------|
| `/onboarding` | 球迷档案三步向导 |
| `/cheer/:matchId` | 助威墙 |
| `/arena` | 球迷擂台（军团贡献 / 球星热力） |
| `/me/card` | 球迷名片 |
| `/legal/ai` | AI 使用与计费说明 |
