# RMB 打新生产上线清单

## 环境变量（`backend/.env`）

- `PRODUCTION_MODE=true`
- `ALIPAY_MOCK=false` + 证书路径完整
- `AVATA_MOCK=false`（若启用文昌链）
- `PUBLIC_API_BASE_URL=https://你的域名`（链 metadata 公网可达）
- `REALNAME_*` 按合规渠道配置

## 验收命令

```bash
cd backend
python scripts/check_production_readiness.py
pytest tests/test_rmb_mint_payment.py -q
alembic upgrade head
```

## 首场 whitelist 内测

```bash
python scripts/setup_whitelist_mint.py --card-code YOUR_CARD --user-ids 1,2,3
```

Admin 可在 `/admin/economy` 查看订单与退款；用户从 `/mint` 进入 RMB 支付。

## E2E 路径

1. Admin 创建/激活打新活动
2. 用户实名（生产渠道）→ 创建订单 → 支付宝支付
3. 回调 fulfill → 序列号 + 链铸造队列
4. `ShopPaymentResult` 轮询链状态
