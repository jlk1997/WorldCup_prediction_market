# 资讯 ingest 设计说明

## 现状（改造前）

- 单一配置 `NEWS_RSS_FEEDS`，默认 **BBC Sport Football RSS**（英文）
- 定时任务 `NewsRssService.sync()` 拉取 → 写入 `news_articles` → `GET /api/news`
- 无 `lang` 字段，前端「资讯流」混合展示，用户感知为全英文

## 目标架构

```
┌─────────────────┐     ┌─────────────────┐
│ NEWS_RSS_FEEDS_EN│     │ NEWS_RSS_FEEDS_ZH│
│ BBC / Guardian  │     │ 虎扑/懂球帝 RSS  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
           NewsRssService.sync()
           · RSS/Atom 解析
           · lang = en | zh
           · 球队标签 → 中文队名
                     ▼
              news_articles (lang)
                     ▼
         GET /api/news?lang=zh|en|all
                     ▼
         前端 Tab：中文资讯 | 国际资讯 | 全部
```

## 中文资讯获取方式（推荐优先级）

| 方式 | 说明 | 推荐度 |
|------|------|--------|
| **RSS 聚合（已实现）** | 配置 `NEWS_RSS_FEEDS_ZH`，支持 RSS 2.0 + Atom | ⭐⭐⭐ 首选 |
| **RSSHub 路由** | 虎扑足球、懂球帝新闻等转为 RSS；可自建 [RSSHub](https://docs.rsshub.app/) | ⭐⭐⭐ |
| **官方/门户 RSS** | 部分门户有体育频道 RSS（更新频率一般） | ⭐⭐ |
| **API 合作** | 商业体育数据 API（成本高，后期可选） | ⭐ 远期 |
| **页面抓取** | 反爬、维护成本高，不推荐 | ❌ |

### 示例配置（`backend/.env`）

```env
NEWS_RSS_FEEDS_EN=https://feeds.bbci.co.uk/sport/football/rss.xml

# 国内可用源（已实测 2026-06）：
# · Google News 中文「世界杯/足球」聚合
# · 人民网体育 RSS
# · 虎扑足球（RSSHub 镜像 rssforever.com，可换自建实例）
NEWS_RSS_FEEDS_ZH=https://news.google.com/rss/search?q=世界杯+足球&hl=zh-CN&gl=CN&ceid=CN:zh-Hans,https://news.google.com/rss/search?q=足球&hl=zh-CN&gl=CN&ceid=CN:zh-Hans,http://www.people.com.cn/rss/sports.xml,https://rsshub.rssforever.com/hupu/soccer
```

## 个性化排序（主队优先）

- 登录用户请求 `GET /api/news?personalize=true`（默认开启）
- 单次 SQL 拉取最近 **100 条**（`NEWS_FETCH_CAP`），内存按主队→副队→时间排序后截取 `limit`
- 结果 **Redis/内存缓存 60 秒**，key 含 lang + 主副队名
- 手动 `?team=阿根廷` 时用 JSONB `@>` 索引过滤，不走全表扫描
- 迁移 `009_news_tags_gin` 为 `team_tags` 建 GIN 索引

## 球队标签

- 库内球队名为**中文**（如「阿根廷」）
- **中文资讯**：标题/摘要直接匹配中文队名 + 媒体别名（国足、潘帕斯等）
- **英文资讯**：通过 `bsd_team_names` 英→中映射，将 Argentina → 阿根廷 写入 `team_tags`

## API

| 接口 | 说明 |
|------|------|
| `GET /api/news?lang=zh` | 中文资讯 |
| `GET /api/news?lang=en` | 国际资讯 |
| `GET /api/news?lang=all` | 全部 |
| `GET /api/news/stats` | 各语言条数（Tab 角标） |
| `POST /api/news/sync` | 手动触发（需 `ALLOW_MANUAL_SYNC=true`） |

## 运维

- 后台 scheduler 每轮 ingest 会同步中英两路 RSS
- 新增文章以 `url` 去重
- 迁移 `008_news_lang` 为历史数据默认 `lang=en`

## 后续可扩展

1. 按用户主队优先排序资讯
2. 中文摘要 LLM 翻译（英文 Tab 内嵌中文摘要）
3. 世界杯专题 RSS 白名单过滤（仅保留 2026 相关关键词）
