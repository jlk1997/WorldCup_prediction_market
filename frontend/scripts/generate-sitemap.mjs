/**
 * Post-build: write dist/sitemap.xml from static public routes.
 * Run: node scripts/generate-sitemap.mjs
 */
import { writeFileSync, readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const distDir = join(root, 'dist')

const siteUrl = (process.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')

const STATIC_PATHS = [
  '/',
  '/worldcup2026',
  '/login',
  '/live',
  '/teams',
  '/players',
  '/news',
  '/leaderboard',
  '/agent',
  '/shop',
  '/legal/terms',
  '/legal/privacy',
  '/legal/ai',
]

function loadTeamPaths() {
  const mappingPath = join(root, '..', 'backend', 'data', 'team_api_mapping.json')
  if (!existsSync(mappingPath)) return []
  try {
    const raw = JSON.parse(readFileSync(mappingPath, 'utf8'))
    const names = Object.keys(raw)
    return names.slice(0, 48).map((name) => `/teams/${encodeURIComponent(name)}`)
  } catch {
    return []
  }
}

const paths = [...STATIC_PATHS, ...loadTeamPaths()]
const today = new Date().toISOString().slice(0, 10)

const urls = paths
  .map(
    (path) => `  <url>
    <loc>${siteUrl}${path === '/' ? '/' : path}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${path === '/' || path === '/news' ? 'daily' : 'weekly'}</changefreq>
    <priority>${path === '/' ? '1.0' : path === '/worldcup2026' ? '0.9' : '0.7'}</priority>
  </url>`,
  )
  .join('\n')

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`

if (!existsSync(distDir)) {
  console.warn('[sitemap] dist/ not found — run vite build first')
  process.exit(0)
}

writeFileSync(join(distDir, 'sitemap.xml'), xml, 'utf8')
console.log(`[sitemap] wrote ${paths.length} URLs to dist/sitemap.xml`)
