#!/usr/bin/env node
/**
 * Verify legend backdrop assets before deploy.
 * Do NOT deploy stadium.glb — use LegendsPageBackdrop only.
 */
import { access, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(fileURLToPath(new URL('.', import.meta.url)), '..', 'public')
const MAX_BACKDROP_BYTES = 400 * 1024

const required = [
  'logo.svg',
  'favicon-32.png',
  'favicon-192.png',
  'apple-touch-icon.png',
  'share-og.png',
  'legends/ronaldo-backdrop.webp',
  'legends/messi-backdrop.webp',
  'legends/neymar-backdrop.webp',
]

const forbidden = ['stadium.glb']

let exitCode = 0

for (const rel of forbidden) {
  try {
    await access(join(root, rel))
    console.error(`FAIL ${rel} must not be deployed (remove to save bandwidth)`)
    exitCode = 1
  } catch {
    console.log(`OK  ${rel} absent`)
  }
}

for (const rel of required) {
  const path = join(root, rel)
  try {
    await access(path)
    const { size } = await stat(path)
    const kb = Math.round(size / 1024)
    if (size > MAX_BACKDROP_BYTES) {
      console.error(`FAIL ${rel} is ${kb}KB (max ${MAX_BACKDROP_BYTES / 1024}KB). Run: python scripts/optimize-legends.py`)
      exitCode = 1
    } else {
      console.log(`OK  ${rel} (${kb}KB)`)
    }
  } catch {
    console.error(`FAIL ${rel} missing — run python scripts/optimize-legends.py`)
    exitCode = 1
  }
}

process.exit(exitCode)
