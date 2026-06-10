# 支付宝证书文件目录

本目录存放 **公钥证书模式** 所需的私钥与证书，**切勿提交到 Git**（已在根目录 `.gitignore` 忽略）。

## 需要的 4 个文件

| 文件（示例名） | 环境变量 | 说明 |
|----------------|----------|------|
| `alipay_app_private.pem` | `ALIPAY_PRIVATE_KEY_PATH` | 应用私钥（生成 CSR 时保存） |
| `appCertPublicKey_xxxx.crt` | `ALIPAY_APP_CERT_PATH` | 应用公钥证书 |
| `alipayCertPublicKey_RSA2.crt` | `ALIPAY_ALIPAY_CERT_PATH` | 支付宝公钥证书 |
| `alipayRootCert.crt` | `ALIPAY_ROOT_CERT_PATH` | 支付宝根证书 |

## 从哪里下载

1. 登录 [支付宝开放平台](https://open.alipay.com)
2. 进入你的应用 → **开发设置** → **接口加签方式**
3. 选择 **公钥证书**，按指引生成 CSR、上传后下载上述三份 `.crt`
4. 应用私钥在本地生成 CSR 时自行保存

## 常见错误

- **不要用** 密钥模式下的「支付宝公钥」字符串或 `alipay_public.pem` — 证书模式不需要该文件
- 沙箱与生产各有 **不同的 AppID 和证书**，切换时需同时改 `.env` 中 `ALIPAY_APP_ID` 与四个文件
- 证书文件需为完整 PEM 格式（含 `BEGIN/END CERTIFICATE` 头尾）

详细接入说明见项目根目录 [`docs/ALIPAY_INTEGRATION.md`](../../docs/ALIPAY_INTEGRATION.md)。
