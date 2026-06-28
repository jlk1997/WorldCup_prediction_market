# 规模化部署指南（Post Phase 15）

## 1. Redis（生产必选）

生产环境 `main.py` 启动时会校验 `REDIS_URL`。用途：

| 模块 | 用途 |
|------|------|
| `AntiCheatService` | 竞猜/打新 IP、用户、设备指纹限频 |
| `ai_concurrency` | 全局限流 LLM 并发槽位 |
| `distributed_lock` | 定时任务/结算互斥 |
| 缓存前缀 | 排行榜、擂台等 `cache_delete_prefix` |

验收：`python scripts/check_production_readiness.py` 在 `PRODUCTION_MODE=true` 时须显示 `REDIS_URL=set`。

Admin Ops 大盘显示 `Redis ON/OFF` 与 AI 队列利用率告警（`AI_QUEUE_ALERT_PCT`，默认 85%）。

## 2. Live Ingest 与 API 进程分离

推荐拓扑：

```
                    ┌─────────────────┐
  赛程/比分源 ─────►│  ingest-worker  │──► PostgreSQL
                    │  (scheduler)    │
                    └─────────────────┘
                              │
                    ┌─────────▼─────────┐
  用户 / CDN ──────►│  api (uvicorn)    │──► Redis
                    │  FastAPI          │
                    └───────────────────┘
```

- **ingest-worker**：仅跑 `app.ingest.scheduler`（比赛同步、结算、比赛日编排、Fantasy 周结）
- **api**：`uvicorn app.main:app`，不启动 scheduler（设置 `ENABLE_BACKGROUND_INGEST=false`）

同库同 Redis；ingest 写库后 API 通过 DB/缓存失效感知更新。

## 3. 反作弊 v2（设备指纹）

前端 `api/client` 自动附带 `X-Device-Id`（localStorage 持久化匿名 ID）。

后端 `AntiCheatService` 在竞猜提交、打新下单时叠加设备维度限频（需 Redis）。

## 4. 运维告警阈值（Admin Ops）

| 指标 | 默认阈值 |
|------|----------|
| 链铸造失败累计 | ≥5 或 24h 内 ≥3 → `chain.alert` |
| AI 队列利用率 | ≥ `AI_QUEUE_ALERT_PCT`（85%）→ `ai.alert` |

## 5. 生产发布清单

1. `PRODUCTION_MODE=true`，`ALIPAY_MOCK=false`，完整支付宝证书
2. `REDIS_URL` 可连
3. `PUBLIC_API_BASE_URL` 公网可访问（链 metadata）
4. `python scripts/check_production_readiness.py` → PASS
5. `alembic upgrade head`（含 `046_season_ultimate_matchday`）
6. 可选：`python scripts/setup_whitelist_mint.py` 首场 RMB 内测
