# 数字资产平台 — 安全与并发说明

## 卡牌对决（PVP）

| 风险 | 缓解 |
|------|------|
| 待应战时卡牌被挂牌/转赠 | 挑战成功后 `lock_state=duel`，取消/过期/结算后释放 |
| 双 accept 并发 | `CardDuel` 行 `FOR UPDATE` + `status=pending` 校验 |
| 用户行死锁 | accept 时按 `user_id` 升序加锁 |
| AI 积分增发 | AI 奖池 = 单份 stake；PVP 奖池 = stake×2 |
| escrow 丢失 | 取消/过期 `duel_stake_refund`，ledger `ref_id=duel.id` 幂等 |
| 刷接口 | 对决 API 每用户 40 次/分钟 |

## 交易行 / 流通

- 挂牌/购买：`User` + `CardListing` 行锁
- 过期挂牌：scheduler + `reconcile_stale_listing` 兜底
- 回购：best-effort 链上 `recalled` 标记

## Fantasy

- `FantasyScoreLog (lineup_id, match_id)` 唯一约束
- 完赛即时计分 + scheduler 双通道，重复调用安全

## 配置项

- `card_duel_pending_expire_hours`（默认 72）
- `card_duel_max_pending_per_user`（默认 5）

## 上线前检查

1. `production_mode=true`，关闭 dev collab 自动 seed
2. 实名 gate 开启于流通/对决/交易
3. 经济看板监控 redeem 净流入
