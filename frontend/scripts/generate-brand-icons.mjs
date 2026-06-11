#!/usr/bin/env node
/** Generate PNG favicon + WeChat share image from public/logo.svg */
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const svg = join(root, 'public', 'logo.svg')
const bg = '#0f1224'

const jobs = [
  ['public/apple-touch-icon.png', 180],
  ['public/favicon-32.png', 32],
  ['public/favicon-192.png', 192],
  ['public/share-og.png', 512],
]

for (const [out, width] of jobs) {
  const r = spawnSync(
    'npx',
    ['--yes', '@resvg/resvg-js-cli', svg, join(root, out), '--fit-width', String(width), '--background', bg],
    { stdio: 'inherit', shell: true },
  )
  if (r.status !== 0) process.exit(r.status ?? 1)
}

console.log('Brand icons generated in public/')
