# 文昌链 AVATA 数字藏品集成

本系统通过 [AVATA 多链服务平台](https://docs.avata.bianjie.ai/) 将球星收藏卡铸造为**文昌链原生 NFT**，由平台托管链账户，符合国内数字藏品合规路径。

## 架构

```mermaid
flowchart LR
  User[用户获得卡牌] --> App[CollectibleService]
  App --> Queue[chain_status=pending]
  Scheduler[Ingest Scheduler] --> ChainSvc[CollectibleChainService]
  ChainSvc --> Avata[AVATA API v3]
  Avata --> Wenchang[文昌链]
  ChainSvc --> Meta[/api/collectible/metadata/id.json]
```

- **玩法层**：仍由竞猜/签到/比赛日驱动掉卡（不变）
- **链层**：首次获得卡牌后异步铸造 NFT，用户无需钱包
- **托管模式**：AVATA 托管链账户私钥，应用方通过 API 代铸造

## 环境变量

### `PUBLIC_API_BASE_URL` 怎么填？

填 **线上对外访问的站点根域名**（与浏览器打开前端的域名一致），**不要**加 `/api` 后缀。

Nginx 把 `/api/` 反代到后端时，正确示例：

```env
PUBLIC_API_BASE_URL=https://loveaibaby.cn
```

元数据 URL 为：`https://loveaibaby.cn/api/collectible/metadata/{id}.json`（须公网无需登录可访问）。

本地开发可留空；真实 AVATA 铸造需公网地址。

在 `backend/.env` 中配置：

```env
# 文昌链 AVATA（数字藏品上链）
AVATA_ENABLED=true
AVATA_MOCK=true          # 开发/无密钥时用 mock，不调用真实 API
AVATA_HOST=https://apis.avata.bianjie.ai
AVATA_API_KEY=请填写
AVATA_API_SECRET=请填写
AVATA_NFT_CLASS_ID=       # 首次运行可留空，会自动创建；建议创建后填入固定值
AVATA_NFT_CLASS_NAME=最后一舞·球星收藏
AVATA_CHAIN_NAME=文昌链
# 创建 NFT 类别时的 owner（应用链账户）。留空则首次上链时自动 create_accounts
AVATA_CLASS_OWNER=
```

### 关于「归集链账户地址」

| 用途 | 是否需要 |
|------|----------|
| **创建 NFT 类别**（`owner` 字段） | **需要** — 必须是应用持有的链地址，可用 AVATA 控制台提供的应用链账户，或 `POST /v3/accounts` 创建后填入 `AVATA_CLASS_OWNER` |
| **铸造 NFT 到用户**（`recipient`） | **不需要归集账户** — 每位用户自动创建 AVATA 托管链账户，NFT 直接铸造到用户本人地址 |

即：控制台里的「归集链账户」若已提供，可填到 `AVATA_CLASS_OWNER`；若未提供，运行 `python -m scripts.setup_avata_collectible` 会自动创建平台地址并创建 NFT 类别。

### 接入步骤（生产）

参考 [AVATA 接入说明](https://docs.avata.bianjie.ai/doc-2728160)：

1. 注册 [AVATA 控制台](https://docs.avata.bianjie.ai/) 并完成企业 KYC
2. 创建项目，下载 `API Key` / `API Secret`
3. 资金账户充值（链账户创建约 0.05 元/个，铸造消耗能量值）
4. 申请「创建 NFT 类别」权限
5. 设置 `AVATA_ENABLED=true`，`AVATA_MOCK=false`
6. 运行 `python -m scripts.setup_avata_collectible` 创建 NFT 类别并写入 class_id

**「归集链账户」说明**：铸造到用户时不需要归集账户；但**创建 NFT 类别**时 API 要求 `owner`（应用链账户地址）。可将控制台提供的地址填入 `AVATA_CLASS_OWNER`，或由 setup 脚本自动创建。

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/collectible/chain/status` | 用户链账户与铸造统计（需登录） |
| `GET /api/collectible/metadata/{user_card_id}.json` | NFT 元数据（公开，供 AVATA uri 引用） |

## 链上状态

`user_collectible_cards.chain_status`：

| 值 | 含义 |
|----|------|
| `none` | 未启用链或未排队 |
| `pending` | 等待 scheduler 铸造 |
| `minting` | 已提交 AVATA，等待上链确认 |
| `minted` | 铸造成功 |
| `failed` | 失败（可查看 chain_error） |

## 合规说明

- NFT 仅作为**玩法获得的荣誉凭证**，不提供转赠/二级市场接口
- 全站文案仍标注「无金钱价值、不可交易」
- 详见 [COLLECTIBLE_COMPLIANCE.md](./COLLECTIBLE_COMPLIANCE.md)

## 相关 AVATA API

- 创建链账户：`POST /v3/accounts`
- 创建 NFT 类别：`POST /v3/native/nft/classes`
- 发行 NFT：`POST /v3/native/nft/nfts/{class_id}`
- 查询上链结果：`GET /v3/native/tx/{operation_id}`

文档：[AVATA 帮助文档](https://docs.avata.bianjie.ai/)
