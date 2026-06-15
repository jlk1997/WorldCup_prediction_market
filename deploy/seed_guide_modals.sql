-- =============================================================================
-- 讲解弹窗 (site_intro) + 玩法弹窗 (gameplay_guide)
-- 在 PostgreSQL 线上库直接执行（需已有 system_ui_configs 表，迁移 029）
--
-- 用法：
--   psql "$DATABASE_URL" -f deploy/seed_guide_modals.sql
--
-- 改文案：直接 UPDATE config 字段；改 version + storage_key 可让老用户再看一遍
-- 接口：GET /api/ui-config/site_intro  |  GET /api/ui-config/gameplay_guide
-- =============================================================================

-- 若表不存在（极少数未跑迁移的环境），先建表
CREATE TABLE IF NOT EXISTS system_ui_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(64) NOT NULL,
    config JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_system_ui_config_key UNIQUE (config_key)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. 讲解弹窗：新用户进站 30 秒看懂「最后一舞」是干什么的
--    触发：首页 / 赛事中心 / 大屏，首次访问自动弹出（localStorage 记一次）
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO system_ui_configs (config_key, config, updated_at)
VALUES (
  'site_intro',
  $json$
{
  "enabled": true,
  "version": 1,
  "storage_key": "wc_site_intro_v1",
  "trigger": {
    "require_login": false,
    "require_profile": false,
    "routes": ["/", "/live", "/dashboard"],
    "auto_open": true,
    "show_once": true,
    "delay_ms": 900
  },
  "dialog": {
    "badge": "30 秒看懂本站",
    "title": "欢迎来到「最后一舞 · 世界杯2026」",
    "subtitle": "看球、竞猜、冲榜 —— 和传奇同框，见证最后一舞（非 FIFA 官方产品）"
  },
  "steps": [
    {
      "icon": "⚽",
      "title": "这是什么地方？",
      "desc": "面向 2026 世界杯的球迷互动站：看赛程比分、玩娱乐竞猜、用 AI 辅助分析，轻松上手。",
      "bullets": [
        "免费注册即可参与大部分玩法",
        "所有奖励均为虚拟道具，不可提现",
        "数据来自公开赛程与实时同步，仅供娱乐"
      ]
    },
    {
      "icon": "📺",
      "title": "能做什么？",
      "desc": "按兴趣选入口，不用一次全搞懂：",
      "bullets": [
        "首页 / 赛事中心：104 场赛程、Live 比分、淘汰赛对阵",
        "竞猜大厅：开赛前猜胜/平/负，猜中得积分冲榜",
        "AI 工作台：赛前 / 赛中 / 赛后多步分析报告",
        "召友中心：邀请球友注册，双方得球迷币"
      ]
    },
    {
      "icon": "🪙",
      "title": "三种「分/币」别搞混",
      "highlight": "球迷币 = 质押用 · 累计积分 = 冲排行榜 · 可用积分 = 商城兑换装扮",
      "bullets": [
        "球迷币：竞猜时可质押，猜中通常双倍返还；也可签到、任务、充值获得",
        "累计积分：猜中、任务、榜奖励获得，决定你在排行榜上的名次",
        "可用积分：猜中时按比例赠送，可在商城兑换头像框等虚拟装扮"
      ]
    },
    {
      "icon": "🚀",
      "title": "建议从这里开始",
      "desc": "第一次来按这个顺序最不容易懵：",
      "bullets": [
        "① 登录并完善档案（选主队，解锁个性化推荐）",
        "② 打开「竞猜大厅」看玩法说明，用每日免费次数试一手",
        "③ 想深度研究再去 AI 工作台生成分析报告"
      ]
    }
  ],
  "footer": {
    "skip": "跳过，我自己逛",
    "prev": "上一步",
    "next": "下一步",
    "finish": "开始探索",
    "secondary_finish": "直接去看竞猜玩法"
  },
  "finish_action": {
    "primary_route": "/live",
    "secondary_route": "/predict"
  }
}
$json$::jsonb,
  now()
)
ON CONFLICT (config_key) DO UPDATE
SET config = EXCLUDED.config,
    updated_at = now();

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. 玩法弹窗：竞猜大厅专用，讲清怎么猜、怎么算分、什么时候开奖
--    触发：登录后首次进入 /predict；也可点右上角「玩法说明」随时再看
--    强制再看：访问 /predict?guide=1
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO system_ui_configs (config_key, config, updated_at)
VALUES (
  'gameplay_guide',
  $json$
{
  "enabled": true,
  "version": 1,
  "storage_key": "wc_gameplay_guide_v1",
  "trigger": {
    "require_login": false,
    "require_profile": false,
    "routes": ["/predict"],
    "auto_open": true,
    "show_once": true,
    "delay_ms": 700,
    "query_param": "guide"
  },
  "dialog": {
    "badge": "竞猜玩法 · 5 步上手",
    "title": "竞猜大厅怎么玩？",
    "subtitle": "娱乐竞猜，开赛前提交、开赛后锁定，猜中得积分与可用积分"
  },
  "steps": [
    {
      "icon": "1️⃣",
      "title": "三步完成一次竞猜",
      "desc": "未登录也可以先看规则；要提交竞猜需要先登录。找到未开赛的比赛卡片，按提示操作即可：",
      "bullets": [
        "登录账号（未完善档案也可猜，但建议先选主队）",
        "选择「主队胜 / 平局 / 客队胜」",
        "开球前点击提交；开球后或已有比分则无法更改"
      ],
      "highlight": "记住：只在开赛前能下注，开赛瞬间系统自动锁单"
    },
    {
      "icon": "🆓",
      "title": "免费次数 vs 质押球迷币",
      "bullets": [
        "每日有免费竞猜次数（签到、任务可额外获得），不消耗球迷币",
        "也可质押球迷币加注：猜中通常返还 2 倍质押；未中则消耗",
        "免费与质押二选一，提交前卡片上会标明当前模式"
      ]
    },
    {
      "icon": "🏆",
      "title": "猜中后得什么？",
      "bullets": [
        "累计积分：用于排行榜（胜/平基础分 + 连胜加成，偶尔有连败保护加成）",
        "可用积分：按一定比例从累计积分折算，可在商城兑换装扮",
        "球迷币：质押模式猜中双倍返还；免费模式猜中也可能有额外小奖励",
        "猜错不扣累计积分，仅质押的球迷币不退（免费次数不受影响）"
      ]
    },
    {
      "icon": "⏱️",
      "title": "什么时候开奖？",
      "desc": "不用手动刷新，系统会自动处理：",
      "bullets": [
        "比赛标记「已结束」且比分齐全后，约 1–3 分钟内自动结算",
        "猜中会弹窗庆祝，也可在「球迷中心 → 竞猜记录」查看",
        "比赛推迟/取消或长期无比分：流局，质押原路退还",
        "有待开奖时页面会提示，可去个人中心查看进度"
      ]
    },
    {
      "icon": "📅",
      "title": "每日任务 & 召友加成",
      "bullets": [
        "每日签到、主队问答、完成免费竞猜 —— 领球迷币和次数",
        "邀请球友注册并完成档案/首猜，双方得币，还可冲召友周榜",
        "顶部「去分享」可复制邀请链接，详情见「召友中心」"
      ]
    }
  ],
  "footer": {
    "skip": "跳过",
    "prev": "上一步",
    "next": "下一步",
    "finish": "知道了，去竞猜",
    "secondary_finish": "去看 AI 分析"
  },
  "finish_action": {
    "primary_route": "/predict",
    "secondary_route": "/agent"
  }
}
$json$::jsonb,
  now()
)
ON CONFLICT (config_key) DO UPDATE
SET config = EXCLUDED.config,
    updated_at = now();

-- 验证
SELECT config_key, jsonb_pretty(config->'dialog') AS dialog_preview, updated_at
FROM system_ui_configs
WHERE config_key IN ('site_intro', 'gameplay_guide')
ORDER BY config_key;
