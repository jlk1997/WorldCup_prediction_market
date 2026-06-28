# 联名 / IP 打新法务 Checklist

上线前逐项确认（Admin → 打新创建）：

- [ ] 版权/肖像权授权文件归档（俱乐部、KOL、球员）
- [ ] 宣传文案不含「投资」「保值」「升值」表述
- [ ] 分享页不展示 RMB 二级价或收益率
- [ ] 用户协议与打新页 18+、虚拟商品、不可提现声明可见
- [ ] 限量与库存与链上铸造能力一致（`check_production_readiness.py` PASS）
- [ ] 退款策略：仅 Admin 原路退款，用户端无自助提现
- [ ] 联名素材来源记录（设计稿、合同编号）
- [ ] 舆情/合规负责人 sign-off

Demo 活动使用 `POST /api/mint-events/admin/seed-collab`，生产活动使用 `admin/events` 且 `competition` 标记联名系列。
