/**
 * Post-build: write dist/sitemap.xml and dist/robots.txt from public routes.
 * Run: node scripts/generate-sitemap.mjs
 */
import { writeFileSync, readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  siteUrl,
  loadTeamNames,
  loadScheduleMatches,
  STATIC_PUBLIC_ROUTES,
} from './seo-build-utils.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const distDir = join(root, 'dist')

const staticPaths = STATIC_PUBLIC_ROUTES.map((r) => r.path)
const teamPaths = loadTeamNames().map((name) => `/teams/${encodeURIComponent(name)}`)
const matchPaths = loadScheduleMatches().map((_, i) => `/live/match/${i + 1}`)
const paths = [...staticPaths, ...teamPaths, ...matchPaths]
const today = new Date().toISOString().slice(0, 10)

const urls = paths
  .map((path) => {
    const loc = path === '/' ? `${siteUrl}/` : `${siteUrl}${path}`
    const changefreq =
      path === '/' || path === '/news' || path.startsWith('/live/match/')
        ? 'daily'
        : 'weekly'
    let priority = '0.7'
    if (path === '/') priority = '1.0'
    else if (path === '/worldcup2026') priority = '0.9'
    else if (path === '/live') priority = '0.85'
    else if (path.startsWith('/teams/')) priority = '0.75'
    else if (path.startsWith('/live/match/')) priority = '0.65'
    return `  <url>
    <loc>${loc}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`
  })
  .join('\n')

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`

const robots = `User-agent: *
Allow: /
Disallow: /me
Disallow: /onboarding
Disallow: /invite
Disallow: /shop/result
Disallow: /api/

Sitemap: ${siteUrl}/sitemap.xml
`

if (!existsSync(distDir)) {
  console.warn('[sitemap] dist/ not found — run vite build first')
  process.exit(0)
}

writeFileSync(join(distDir, 'sitemap.xml'), xml, 'utf8')
writeFileSync(join(distDir, 'robots.txt'), robots, 'utf8')
console.log(`[sitemap] wrote ${paths.length} URLs to dist/sitemap.xml`)
console.log(`[sitemap] wrote dist/robots.txt (Sitemap: ${siteUrl}/sitemap.xml)`)
