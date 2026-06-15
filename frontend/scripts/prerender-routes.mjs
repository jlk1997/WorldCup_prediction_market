/**
 * Post-build: inject route-specific meta into static index.html copies for SEO crawlers.
 * Run: node scripts/prerender-routes.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = join(__dirname, '..', 'dist')
const siteUrl = (process.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')

const ROUTES = [
  {
    path: '/',
    file: 'index.html',
    title: '最后一舞：世界杯2026',
    description:
      '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
  },
  {
    path: '/worldcup2026',
    file: 'worldcup2026/index.html',
    title: '2026 世界杯球迷指南 — 竞猜、赛程、AI 分析 | 最后一舞',
    description:
      '2026 美加墨世界杯球迷互动指南：免费注册参与娱乐竞猜、实时赛程、球队库、AI 分析与排行榜。',
  },
  {
    path: '/login',
    file: 'login/index.html',
    title: '登录 / 注册 — 最后一舞 · 世界杯2026',
    description: '邮箱验证码登录，新用户自动注册并赠送球迷币。邀请链接注册可获额外奖励。',
  },
  {
    path: '/teams',
    file: 'teams/index.html',
    title: '2026 世界杯球队库 — 最后一舞',
    description: '48 支世界杯参赛球队资料、阵容与球迷互动入口。',
  },
  {
    path: '/news',
    file: 'news/index.html',
    title: '世界杯资讯 — 最后一舞',
    description: '2026 世界杯相关新闻与 RSS 聚合资讯。',
  },
]

function injectMeta(html, { title, description, path }) {
  const url = path === '/' ? `${siteUrl}/` : `${siteUrl}${path}`
  return html
    .replace(/<title>[^<]*<\/title>/, `<title>${title}</title>`)
    .replace(/content="__SITE_DESCRIPTION__"/g, `content="${description}"`)
    .replace(/content="__SITE_TITLE__"/g, `content="${title}"`)
    .replace(/content="__SITE_URL__\//g, `content="${url}`)
    .replace(/content="__SITE_URL__\/share-og.png"/g, `content="${siteUrl}/share-og.png"`)
    .replace(/__SITE_TITLE__/g, title)
    .replace(/__SITE_DESCRIPTION__/g, description)
    .replace(/__SITE_URL__/g, siteUrl)
}

if (!existsSync(join(distDir, 'index.html'))) {
  console.warn('[prerender] dist/index.html missing — skip')
  process.exit(0)
}

const baseHtml = readFileSync(join(distDir, 'index.html'), 'utf8')

for (const route of ROUTES) {
  const html = injectMeta(baseHtml, route)
  const outPath = join(distDir, route.file)
  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, html, 'utf8')
  console.log(`[prerender] ${route.path} -> ${route.file}`)
}

console.log('[prerender] done')
