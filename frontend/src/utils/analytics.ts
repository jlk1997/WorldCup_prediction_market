declare global {
  interface Window {
    _hmt?: unknown[]
    umami?: { track: (name: string, data?: Record<string, string>) => void }
  }
}

const umamiWebsiteId = import.meta.env.VITE_UMAMI_WEBSITE_ID as string | undefined
const umamiScriptUrl = import.meta.env.VITE_UMAMI_SCRIPT_URL as string | undefined
const baiduTongjiId = import.meta.env.VITE_BAIDU_TONGJI_ID as string | undefined

let initialized = false

export function initAnalytics() {
  if (initialized || typeof document === 'undefined') return
  initialized = true

  if (umamiWebsiteId && umamiScriptUrl) {
    const s = document.createElement('script')
    s.async = true
    s.defer = true
    s.src = umamiScriptUrl
    s.setAttribute('data-website-id', umamiWebsiteId)
    document.head.appendChild(s)
  }

  if (baiduTongjiId) {
    window._hmt = window._hmt || []
    const s = document.createElement('script')
    s.async = true
    s.src = `https://hm.baidu.com/hm.js?${baiduTongjiId}`
    document.head.appendChild(s)
  }
}

export function trackEvent(name: string, data?: Record<string, string | number | boolean>) {
  const payload = data
    ? Object.fromEntries(Object.entries(data).map(([k, v]) => [k, String(v)]))
    : undefined

  try {
    window.umami?.track(name, payload)
  } catch {
    /* ignore */
  }

  try {
    if (window._hmt && baiduTongjiId) {
      window._hmt.push(['_trackEvent', 'wc2026', name, JSON.stringify(payload ?? {})])
    }
  } catch {
    /* ignore */
  }
}
