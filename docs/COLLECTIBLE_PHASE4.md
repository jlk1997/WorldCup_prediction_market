# Phase 4：收藏通知 + 比赛日限定卡

## 站内通知

| 事件 | category | 顶栏入口 |
|------|----------|----------|
| 获得球星卡/碎片 | `collectible_drop` | 🃏 CollectibleNotifier |
| 套组奖励领取 | `collectible_set` | 同上 |
| 文昌链铸造完成 | `collectible_chain` | 同上 |

掉卡通知与开包动效并存：在线时弹窗 + 离线/切 tab 时顶栏角标。

## 比赛日限定卡

- 每队一张 `matchday_{team_id}`，系列 `matchday_limited`，史诗稀有度
- 仅 `matchday` 来源可掉落；比赛日动员约 42% 直接掉限定卡
- 同步目录：`python -m scripts.sync_collectible_catalog`

## PUBLIC_API_BASE_URL

生产填 `https://loveaibaby.cn`（根域名，无 `/api`）。详见 [AVATA_INTEGRATION.md](./AVATA_INTEGRATION.md)。
