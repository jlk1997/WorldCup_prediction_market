# 实名认证对接说明

## 当前实现（开发 / 演示）

- 服务：`backend/app/services/realname_service.py`
- 默认 **mock 模式**：用户提交姓名 + 身份证号，服务端哈希存储，标记 `real_name_verified=true`
- 明文不落库；仅保留 `real_name_hash`、`id_no_hash`

## 生产对接点

### 1. 配置开关

在 `config.py` 或环境变量增加（示例）：

```
REALNAME_PROVIDER=aliyun|tencent|mock
REALNAME_API_KEY=...
REALNAME_API_SECRET=...
```

`realname_service.verify()` 内按 provider 分支调用第三方 API。

### 2. 需改造的方法

| 方法 | 职责 |
|------|------|
| `RealNameService.verify(user, real_name, id_no)` | 调第三方二要素/三要素核验 |
| `RealNameService.assert_real_name(user)` | 流通 / 交易 / PVP 前 gate（已实现） |

### 3. 第三方常见流程

1. 用户提交姓名 + 身份证号
2. 后端调用云厂商「身份二要素」接口
3. 成功：写 verified 标记 + 时间戳；失败：返回业务错误，不标记
4. 限流：同一用户 / IP 日次数上限（防刷）

### 4. 合规要求

- 最小必要原则：不存明文身份证
- 未成年人：与登录 `age_confirmed` 联动
- 日志：仅记录 request_id / 结果码，不记明文

### 5. 前端

- `useAssetRealname.ts` — 缓存实名状态
- 交易行 / 转赠 / 卡牌对决前弹窗引导认证

## 测试

- 开发环境继续使用 mock
- 集成测试可用 fixture 用户 + `verify()` mock 路径
