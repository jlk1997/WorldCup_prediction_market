import { LEGEND_CARDS } from '@/data/legends'

const warmed = new Set<string>()
let warmPromise: Promise<void> | null = null

function warmOne(url: string): Promise<void> {
  if (warmed.has(url)) return Promise.resolve()
  return new Promise((resolve) => {
    const img = new Image()
    img.decoding = 'async'
    img.onload = () => {
      warmed.add(url)
      resolve()
    }
    img.onerror = () => {
      warmed.add(url)
      resolve()
    }
    img.src = url
  })
}

function injectPreload(url: string) {
  if (typeof document === 'undefined' || warmed.has(url)) return
  const existing = document.querySelector(`link[rel="preload"][href="${url}"]`)
  if (existing) return
  const link = document.createElement('link')
  link.rel = 'preload'
  link.as = 'image'
  link.href = url
  document.head.appendChild(link)
}

/** Warm HTTP + memory cache for legend backdrop images (call once at app boot). */
export function warmLegendBackdropImages(urls = LEGEND_CARDS.map((c) => c.imageBackdrop)): Promise<void> {
  if (!warmPromise) {
    for (const url of urls) injectPreload(url)
    warmPromise = Promise.all(urls.map(warmOne)).then(() => {})
  }
  return warmPromise
}

export function isLegendImageWarmed(url: string): boolean {
  return warmed.has(url)
}
