<div align="center">
  <img src="frontend/public/icons.svg" width="120" alt="Logo">
  <h1>WC2026 智能辅助决策引擎</h1>
  <p><i>基于 MiniMax 大模型与海量足球数据的赛事分析系统</i></p>
</div>

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3, Vite, Element Plus, Three.js, TypeScript |
| 后端 | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic Settings |
| 数据库 | PostgreSQL 14+ |
| AI | MiniMax（OpenAI 兼容 API） |
| 部署 | Docker Compose（可选） |

---

## AI 多 Agent 分析链

分析请求 `POST /api/agent/analyze` 会依次执行：

1. **DataAgent** — 自动拉取球队档案、伤病、交锋、实时比分；并尝试 LLM Tool Calling 补充查询  
2. **NewsAgent** — LLM 归纳 RSS 新闻舆情摘要  
3. **TacticalAgent** — LLM 生成战术对位与关键对位  
4. **PredictAgent** — LLM 综合输出预测比分、胜率、关键因素  
5. **CriticAgent** — LLM 对照事实包自检，校准置信度并标记矛盾  

`mode` 参数：`pre_match`（赛前）| `live`（赛中，注入比分/事件）| `post_match`（赛后复盘）

---

```
frontend (10087)  ──HTTP──>  backend/app (10086)
                                  ├── api/routes      路由层
                                  ├── ingest/           数据采集（API-Football / RSS）
                                  ├── agents/           多 Agent 编排
                                  ├── db/repositories 数据访问
                                  └── db/models       SQLAlchemy ORM
                                        │
                                   PostgreSQL
```

**核心 API**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针（含 DB） |
| GET | `/api/schedule` | 赛程 |
| GET | `/api/teams` | 球队列表 |
| GET | `/api/team/{name}` | 球队详情 + 球员 |
| GET | `/api/players/{id}` | 球员详情 |
| GET | `/api/sync/status` | 数据采集健康 |
| POST | `/api/sync/run` | 手动触发 live + RSS 同步 |
| GET | `/api/agent/runs` | Agent 分析历史 |
| GET | `/api/stats/overview` | 大屏统计（球队/赛程/Live 数） |
| GET | `/api/teams/compare` | 两队实力对比 |
| `python -m scripts.init_db --full-schedule` | 初始化时导入 104 场 |
| GET | `/api/live/quota` | API-Football 每日配额 |
| GET | `/api/live/matches` | 实时赛程与比分 |
| GET | `/api/news` | RSS 新闻聚合 |
| POST | `/api/agent/analyze` | 多 Agent 赛事分析 |
| WS | `/ws/live` | 实时比分推送 |
| POST | `/api/predict/analysis` | 兼容旧接口（转发 Agent） |
| POST | `/api/predict` | FIFA 排名胜率 |

---

## 本地开发

### 1. 后端（推荐 conda）

```bash
conda activate wc2026
cd backend
cp .env.example .env   # 填写 DB_PASSWORD、MINIMAX_API_KEY、API_FOOTBALL_KEY（可选）

pip install -r requirements.txt
pip install -r requirements-dev.txt   # 可选：pytest

# 首次初始化
python -m scripts.init_db
python -m scripts.sync_teams --source wc2026
python -m scripts.update_starters

# 启动
python run.py
# 或: uvicorn app.main:app --host 0.0.0.0 --port 10086 --reload
```

已有旧库：`alembic upgrade head` 或 `alembic stamp head` 后 `python -m scripts.init_db --seed-only`

# 数据采集 worker（独立进程，可选）
python -m app.ingest.scheduler --once   # 单次同步
python -m app.ingest.scheduler          # 循环轮询

### 2. 前端

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

访问 http://localhost:10087

### 3. 测试

```bash
cd backend
pytest -m "not integration"
pytest   # 含需数据库的集成测试
```

---

## 裸机部署（生产推荐）

### 前置依赖

1. 安装 **PostgreSQL 14+**、**Redis 7+**，并设置开机自启
2. 安装 **Python 3.12**、**Node 20**（仅构建前端静态资源时需要）
3. 防火墙仅开放 **443**（及 **22** 管理）；**不要**对公网暴露 5432 / 6379 / 10086

### 初始化

```bash
cd backend
# 填写 backend/.env（见下方 ingest 二选一）
alembic upgrade head
python -m scripts.init_db
python -m scripts.sync_teams --source wc2026
```

### 数据采集 ingest 二选一

| 方案 | backend `.env` | 额外进程 |
|------|----------------|----------|
| **A（推荐单进程）** | `ENABLE_BACKGROUND_INGEST=true` | 无；API 进程内后台线程轮询，通过 Redis 分布式锁避免重复 |
| **B（独立 worker）** | `ENABLE_BACKGROUND_INGEST=false` | systemd 单独跑 `python -m app.ingest.scheduler` |

**切勿**同时开启后台 ingest 与独立 scheduler，否则会双份轮询 BSD 接口。

### systemd 示例

`/etc/systemd/system/wc2026-api.service`：

```ini
[Unit]
Description=WC2026 API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=wc2026
WorkingDirectory=/opt/wc2026/backend
EnvironmentFile=/opt/wc2026/backend/.env
ExecStart=/opt/wc2026/backend/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

方案 B 另建 `wc2026-ingest.service`：

```ini
[Unit]
Description=WC2026 Ingest Worker
After=network.target postgresql.service redis.service wc2026-api.service

[Service]
Type=simple
User=wc2026
WorkingDirectory=/opt/wc2026/backend
EnvironmentFile=/opt/wc2026/backend/.env
Environment=ENABLE_BACKGROUND_INGEST=false
ExecStart=/opt/wc2026/backend/.venv/bin/python -m app.ingest.scheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

启用：`systemctl enable --now wc2026-api wc2026-ingest`（方案 B 才需要 ingest 单元）。

### Nginx 反代（HTTPS + WSS）

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain/privkey.pem;
    add_header Strict-Transport-Security "max-age=31536000" always;

    root /opt/wc2026/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:10086;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:10086;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

前端构建时注入生产 API 地址：

```bash
cd frontend
VITE_API_BASE_URL=https://your-api-domain.com VITE_WS_URL=wss://your-api-domain.com/ws/live npm run build
```

### 上线前 `.env` 检查

- `PRODUCTION_MODE=true`
- `REDIS_URL=redis://127.0.0.1:6379/0`
- `ALIPAY_MOCK=false`、`ALIPAY_SANDBOX=false`
- `CORS_ORIGINS` 为 HTTPS 前端域名（不含 localhost）
- `JWT_SECRET` ≥ 32 字符强随机串
- `ADMIN_SYNC_SECRET` 已设置（若 `ALLOW_MANUAL_SYNC=true`）

---

## Docker Compose（可选）

```bash
# 需先在 backend/.env 配置 MINIMAX_API_KEY
docker compose up -d postgres redis
# 宿主机初始化一次
cd backend && alembic upgrade head && python -m scripts.init_db && python -m scripts.sync_teams --source wc2026
docker compose up backend ingest-worker
```

---

## 环境变量

**backend/.env** — 见 [backend/.env.example](backend/.env.example)

**frontend/.env** — 见 [frontend/.env.example](frontend/.env.example)

---

## 数据同步说明

| 命令 | 作用 |
|------|------|
| `python -m scripts.init_db` | Alembic 建表 + 48 队 + 赛程 |
| `python -m scripts.sync_teams --source wc2026` | 从 `WorldCup2026_Teams/` 导入详细球员（推荐） |
| `python -m scripts.sync_teams --source legacy` | 仅补充 `球队信息.json` 中的教练/阵型元数据 |
| `python -m scripts.sync_teams --source all` | legacy 元数据 + wc2026 球员 |
| `python -m scripts.expand_schedule --apply` | 本地生成 104 场并写入数据库 |
| `python -m app.ingest.scheduler` | Live 比分 + RSS 定时同步 |

### 3D 性能模式

前端 `localStorage` 键 `wc2026_stadium_mode`：`auto`（默认）| `high` | `balanced` | `lite`（无 Three.js）

---

## 声明

本系统分析结果仅供参考，不构成任何投资或投注建议。
