/**
 * Post-build: generate static HTML shells for match detail SEO landing pages.
 * Run: node scripts/generate-seo-pages.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  injectMeta,
  pathToFile,
  loadScheduleMatches,
  matchRouteMeta,
} from './seo-build-utils.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const distDir = join(__dirname, '..', 'dist')

if (!existsSync(join(distDir, 'index.html'))) {
  console.warn('[seo-pages] dist/index.html missing — skip')
  process.exit(0)
}

const baseHtml = readFileSync(join(distDir, 'index.html'), 'utf8')
const matches = loadScheduleMatches()

if (!matches.length) {
  console.warn('[seo-pages] no schedule_full.json matches — skip')
  process.exit(0)
}

let count = 0
matches.forEach((match, index) => {
  const matchId = index + 1
  const route = matchRouteMeta(match, matchId)
  const html = injectMeta(baseHtml, route)
  const outPath = join(distDir, pathToFile(route.path))
  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, html, 'utf8')
  count++
})

console.log(`[seo-pages] wrote ${count} match landing pages`)
