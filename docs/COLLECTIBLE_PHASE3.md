# 球星收藏卡系统 — Phase 3 变更说明

## 留存闭环（对齐增长痛点）

| 行为 | 之前 | 现在 |
|------|------|------|
| 签到 3/7/14 天 | 后端掉卡，前端无感知 | 全局 `CardRevealDialog` 开包 |
| 比赛日动员 | 仅 toast | 掉卡时自动开包 + 按钮下提示文案 |
| 竞猜页新用户 | 无收藏动机 | `CollectibleHookBanner` 引导 |
| 猜中 | 28% 概率不掉卡 | **猜中必掉**（胜场极少时不再空包） |
| 邀请好友 | 仅被邀请人得卡 | 邀请人在 profile/first_action 也得卡 |

## 新增 API

- `GET /api/collectible/summary` — 收藏进度 + 下一签到里程碑
- `GET /api/collectible/activity` — 最近获得记录
- `GET /api/collectible/costs` — 合成/升星成本表
- `GET /api/collectible/album?series=&owned_only=` — 筛选
- `POST /api/collectible/chain/retry/{user_card_id}` — 铸造失败重试

## 前端入口

- `App.vue` 挂载 `CollectibleDropHost`
- `stores/collectibleRevealStore.ts` — 任意页面调用 `openCollectibleReveal(drop)`

## 运维

```bash
# 回填球星卡队徽占位图
cd backend && python -m scripts.sync_collectible_catalog
```

## Phase 4 建议（未实现）

见主规划 `球星收藏卡数字藏品系统_85c1ba40.plan.md` Phase 4 表。
