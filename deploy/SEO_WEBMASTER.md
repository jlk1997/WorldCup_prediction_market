# 站长平台与 SEO 运营清单

站点：`https://loveaibaby.cn`  
Sitemap：`https://loveaibaby.cn/sitemap.xml`  
Robots：`https://loveaibaby.cn/robots.txt`（构建时按 `VITE_SITE_URL` 生成）

## 1. Google Search Console

1. 打开 [Google Search Console](https://search.google.com/search-console)
2. 添加资源 → 网址前缀 → `https://loveaibaby.cn`
3. 验证方式（任选其一）：
   - **HTML 标签**：在 `frontend/.env` 配置 `VITE_GOOGLE_SITE_VERIFICATION=xxx`，重新构建部署
   - **DNS TXT**：在域名解析添加 Google 提供的 TXT 记录
4. 验证通过后：**站点地图** → 提交 `https://loveaibaby.cn/sitemap.xml`
5. 每周查看：索引页数、抓取错误、核心网页指标

## 2. 百度搜索资源平台

1. 打开 [百度搜索资源平台](https://ziyuan.baidu.com/)
2. 用户中心 → 站点管理 → 添加 `https://loveaibaby.cn`
3. 验证方式：
   - **HTML 标签**：配置 `VITE_BAIDU_SITE_VERIFICATION=xxx` 后重新构建
   - 或上传 `baidu_verify_xxx.html` 到 `frontend/public/` 后部署
4. 链接提交 → **sitemap** → 提交 `https://loveaibaby.cn/sitemap.xml`
5. 开启「普通收录」/「快速抓取」（如有）
6. 每周：`site:loveaibaby.cn` 检查收录量

## 3. 百度统计

1. 登录 [百度统计](https://tongji.baidu.com/)
2. 新建站点 `loveaibaby.cn`，获取 **hm.js 中的站点 ID**
3. 在 `frontend/.env` 配置：
   ```
   VITE_BAIDU_TONGJI_ID=你的站点ID
   ```
4. 重新构建并部署前端
5. 在统计后台查看：来源搜索词、落地页、跳出率

## 4. 部署后自检

```bash
# 首页 meta 是否独立（非占位符）
curl -s https://loveaibaby.cn/teams/阿根廷/ | grep -E 'og:title|description'

# sitemap 是否可访问
curl -sI https://loveaibaby.cn/sitemap.xml

# 分享 OG 页（需 Nginx 反代 /share/ 到后端）
curl -s https://loveaibaby.cn/share/invite | grep og:title
```

## 5. 预期时间线

| 阶段 | 动作 | 预期 |
|------|------|------|
| 第 1 周 | 提交 sitemap + 百度统计上线 | 开始抓取 |
| 第 2–4 周 | 外链软文 2–3 篇（见 `SEO_CONTENT_OUTREACH.md`） | 品牌词/球队长尾开始收录 |
| 第 4–8 周 | 持续更新 FAQ、赛程页 | 长尾词稳定进量 |

**注意**：「世界杯 2026」等大词很难靠前，重点盯「最后一舞」「{球队名} 世界杯 2026 阵容」等长尾。
