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

/** 增长漏斗标准事件名（与 deploy/GROWTH_OPS.md 对齐） */
export const FunnelEvents = {
  registerSuccess: 'register_success',
  inviteBound: 'invite_bound',
  onboardingComplete: 'onboarding_complete',
  tourFinish: 'tour_finish',
  tourSkip: 'tour_skip',
  firstPredictSubmit: 'first_predict_submit',
  predictCoachShow: 'predict_coach_show',
  predictCoachComplete: 'predict_coach_complete',
  starterPackOfferShow: 'starter_pack_offer_show',
  starterPackOfferAccept: 'starter_pack_offer_accept',
  shareMatchInvite: 'share_match_invite',
} as const

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

  void postAnalyticsEvent(name, payload)
}

const ANALYTICS_ALLOW = new Set([
  'predict_follow_ai',
  'predict_submit',
  'share_poster_open',
  'share_poster_copy',
  'mint_order_create',
  'mint_order_paid',
  'ai_analysis_start',
  'ai_analysis_complete',
  'collectible_share_open',
  'chain_mint_success',
  'chain_mint_failed',
])

async function postAnalyticsEvent(name: string, payload?: Record<string, string>) {
  if (!ANALYTICS_ALLOW.has(name)) return
  try {
    const { apiClient } = await import('../api/client')
    await apiClient.post('/api/analytics/event', {
      event_name: name.replace(/-/g, '_'),
      payload: payload ?? {},
    })
  } catch {
    /* ignore */
  }
}

export function trackFunnel(
  step: keyof typeof FunnelEvents,
  data?: Record<string, string | number | boolean>,
) {
  trackEvent(FunnelEvents[step], data)
}
