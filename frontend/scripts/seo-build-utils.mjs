/**
 * Shared helpers for post-build SEO scripts (prerender, sitemap, match pages).
 */
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
export const frontendRoot = join(__dirname, '..')
export const repoRoot = join(frontendRoot, '..')

export const siteUrl = (process.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')

export function escapeAttr(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** Replace title / description / OG / canonical on already-built index.html. */
export function injectMeta(html, { title, description, path, bodySnippet, jsonLd }) {
  const url = path === '/' ? `${siteUrl}/` : `${siteUrl}${path}`
  let out = html
    .replace(/<title>[^<]*<\/title>/, `<title>${escapeAttr(title)}</title>`)
    .replace(
      /<meta name="description" content="[^"]*"/,
      `<meta name="description" content="${escapeAttr(description)}"`,
    )
    .replace(
      /<meta property="og:title" content="[^"]*"/,
      `<meta property="og:title" content="${escapeAttr(title)}"`,
    )
    .replace(
      /<meta property="og:description" content="[^"]*"/,
      `<meta property="og:description" content="${escapeAttr(description)}"`,
    )
    .replace(
      /<meta property="og:url" content="[^"]*"/,
      `<meta property="og:url" content="${escapeAttr(url)}"`,
    )
    .replace(
      /<meta itemprop="name" content="[^"]*"/,
      `<meta itemprop="name" content="${escapeAttr(title)}"`,
    )
    .replace(
      /<meta itemprop="description" content="[^"]*"/,
      `<meta itemprop="description" content="${escapeAttr(description)}"`,
    )

  if (bodySnippet) {
    const noscript = `<noscript class="seo-prerender-body"><article>${bodySnippet}</article></noscript>`
    out = out.replace('<div id="app">', `<div id="app">${noscript}`)
  }

  if (jsonLd) {
    const script = `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`
    out = out.replace('</head>', `${script}\n  </head>`)
  }

  return out
}

export function pathToFile(path) {
  if (path === '/') return 'index.html'
  const trimmed = path.replace(/^\//, '').replace(/\/$/, '')
  return `${trimmed}/index.html`
}

export function loadTeamNames() {
  const mappingPath = join(repoRoot, 'backend', 'data', 'team_api_mapping.json')
  if (!existsSync(mappingPath)) return []
  try {
    const raw = JSON.parse(readFileSync(mappingPath, 'utf8'))
    return Object.keys(raw)
      .filter((name) => !name.startsWith('_'))
      .slice(0, 48)
  } catch {
    return []
  }
}

export function loadScheduleMatches() {
  const schedulePath = join(repoRoot, 'backend', 'schedule_full.json')
  if (!existsSync(schedulePath)) return []
  try {
    return JSON.parse(readFileSync(schedulePath, 'utf8'))
  } catch {
    return []
  }
}

export const STATIC_PUBLIC_ROUTES = [
  {
    path: '/',
    title: '最后一舞：世界杯2026',
    description:
      '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
  },
  {
    path: '/worldcup2026',
    title: '2026 世界杯球迷指南 — 竞猜、赛程、AI 分析 | 最后一舞',
    description:
      '2026 美加墨世界杯球迷互动指南：免费注册参与娱乐竞猜、实时赛程、球队库、AI 分析与排行榜。',
  },
  {
    path: '/login',
    title: '登录 / 注册 — 最后一舞 · 世界杯2026',
    description: '邮箱验证码登录，新用户自动注册并赠送球迷币。邀请链接注册可获额外奖励。',
  },
  {
    path: '/live',
    title: '2026 世界杯赛程与 Live 比分 — 赛事中心 | 最后一舞',
    description:
      '2026 美加墨世界杯完整赛程、实时比分、淘汰赛对阵与 AI 赛前分析入口。免费查看 104 场比赛安排。',
    bodySnippet:
      '<h1>2026 世界杯赛事中心</h1><p>查看小组赛与淘汰赛赛程、Live 比分，关注主队比赛并参与娱乐竞猜。</p>',
  },
  {
    path: '/teams',
    title: '2026 世界杯球队库 — 48 支参赛队 | 最后一舞',
    description: '48 支世界杯参赛球队资料、阵容、球星与球迷互动入口。',
  },
  {
    path: '/players',
    title: '2026 世界杯球员库 — 球星资料 | 最后一舞',
    description: '2026 世界杯参赛球员名单、俱乐部与国家队资料，支持搜索浏览。',
    bodySnippet:
      '<h1>2026 世界杯球员库</h1><p>浏览参赛球星资料，了解各队核心球员与俱乐部背景。</p>',
  },
  {
    path: '/news',
    title: '世界杯资讯 — 最后一舞',
    description: '2026 世界杯相关新闻与 RSS 聚合资讯。',
  },
  {
    path: '/leaderboard',
    title: '球迷排行榜 — 积分 · 军团 · 准度 | 最后一舞',
    description: '累计积分、可用积分、竞猜准度与召友榜 — 2026 世界杯娱乐排行。',
  },
  {
    path: '/agent',
    title: '世界杯 AI 分析 — 赛前 / 赛中解读 | 最后一舞',
    description:
      'AI 多步分析世界杯对阵：战术、伤病、历史交锋与赛果参考。虚拟球迷币消费，仅供娱乐。',
    bodySnippet:
      '<h1>世界杯 AI 分析</h1><p>选择对阵获取 AI 赛前/赛中解读，辅助娱乐竞猜决策。</p>',
  },
  {
    path: '/shop',
    title: '球迷商城 — 虚拟道具 | 最后一舞',
    description: '购买球迷币、赛季通行证与虚拟装扮。虚拟物品不可提现。',
  },
  {
    path: '/legal/terms',
    title: '用户服务协议 — 最后一舞',
    description: '最后一舞平台用户服务协议、虚拟球迷币规则与竞猜免责声明。',
  },
  {
    path: '/legal/privacy',
    title: '隐私政策 — 最后一舞',
    description: '最后一舞隐私政策：数据收集、AI 处理与账号注销说明。',
  },
  {
    path: '/legal/ai',
    title: 'AI 使用说明 — 最后一舞',
    description: 'AI 分析功能的数据处理方式与第三方模型说明。',
  },
]

export function teamRouteMeta(teamName) {
  return {
    path: `/teams/${encodeURIComponent(teamName)}`,
    title: `${teamName} 2026 世界杯 — 阵容 · 赛程 | 最后一舞`,
    description: `${teamName} 2026 美加墨世界杯球队页：赛程、阵容球星、球迷助威与娱乐竞猜入口。`,
    bodySnippet: `<h1>${escapeHtml(teamName)} · 2026 世界杯</h1><p>查看 ${escapeHtml(teamName)} 世界杯赛程、阵容与球迷互动。</p>`,
  }
}

export function matchRouteMeta(match, matchId) {
  const { team1, team2, date, time, stadium, group } = match
  const label = `${team1} vs ${team2}`
  const path = `/live/match/${matchId}`
  const when = [date, time].filter(Boolean).join(' ')
  const descParts = [
    `${label} 2026 世界杯赛程`,
    when ? `开赛 ${when}` : '',
    stadium || '',
    group || '',
  ].filter(Boolean)
  return {
    path,
    title: `${label} — 2026 世界杯赛程 | 最后一舞`,
    description: `${descParts.join(' · ')}。查看比分、AI 分析与娱乐竞猜。`,
    bodySnippet: `<h1>${escapeHtml(label)}</h1><p>${escapeHtml(descParts.join(' · '))}</p><p><a href="${siteUrl}/live">返回赛事中心</a></p>`,
    jsonLd: {
      '@context': 'https://schema.org',
      '@type': 'SportsEvent',
      name: label,
      startDate: when || undefined,
      location: stadium ? { '@type': 'Place', name: stadium } : undefined,
      homeTeam: { '@type': 'SportsTeam', name: team1 },
      awayTeam: { '@type': 'SportsTeam', name: team2 },
      url: `${siteUrl}${path}`,
    },
  }
}
