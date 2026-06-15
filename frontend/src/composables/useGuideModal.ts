import { reactive, ref } from 'vue'
import { getUiConfig, type GuideModalConfig } from '@/api/uiConfig'
import { authState, isLoggedIn } from '@/stores/authStore'

export const guideModalState = reactive({
  open: false,
  configKey: '' as string,
  config: null as GuideModalConfig | null,
  step: 0,
  forced: false,
})

const configCache = new Map<string, GuideModalConfig>()

export async function loadGuideConfig(key: string): Promise<GuideModalConfig | null> {
  if (configCache.has(key)) return configCache.get(key)!
  try {
    const cfg = await getUiConfig<GuideModalConfig>(key)
    if (cfg?.enabled !== false) {
      configCache.set(key, cfg)
      return cfg
    }
  } catch {
    /* missing config */
  }
  return null
}

function routeMatches(path: string, routes?: string[]) {
  if (!routes?.length) return true
  return routes.some((r) => path === r || path.startsWith(`${r}/`))
}

function hasSeen(cfg: GuideModalConfig) {
  try {
    return !!localStorage.getItem(cfg.storage_key)
  } catch {
    return false
  }
}

export function markGuideSeen(cfg: GuideModalConfig) {
  try {
    localStorage.setItem(cfg.storage_key, String(cfg.version || 1))
  } catch {
    /* ignore */
  }
}

export function resetGuideSeen(storageKey: string) {
  try {
    localStorage.removeItem(storageKey)
  } catch {
    /* ignore */
  }
}

export function shouldAutoOpenGuide(
  cfg: GuideModalConfig,
  path: string,
  query: Record<string, unknown>,
): boolean {
  if (!cfg.enabled) return false
  const t = cfg.trigger || {}
  if (t.require_login && !isLoggedIn.value) return false
  if (t.require_profile && !authState.user?.profile_completed) return false
  if (!routeMatches(path, t.routes)) return false
  const qp = t.query_param
  if (qp) {
    const v = query[qp]
    if (v === '1' || v === 'true' || v === 1) return true
  }
  if (!t.auto_open) return false
  if (t.show_once && hasSeen(cfg)) return false
  return true
}

export function openGuideModal(key: string, cfg: GuideModalConfig, forced = false) {
  guideModalState.configKey = key
  guideModalState.config = cfg
  guideModalState.step = 0
  guideModalState.forced = forced
  guideModalState.open = true
}

export function closeGuideModal(markSeen = true) {
  const cfg = guideModalState.config
  if (markSeen && cfg && !guideModalState.forced) {
    markGuideSeen(cfg)
  }
  guideModalState.open = false
  guideModalState.step = 0
  guideModalState.forced = false
}

const pendingKeys = ref<string[]>([])

export async function tryAutoOpenGuide(
  key: string,
  path: string,
  query: Record<string, unknown>,
) {
  const cfg = await loadGuideConfig(key)
  if (!cfg) return
  if (!shouldAutoOpenGuide(cfg, path, query)) return
  if (guideModalState.open) {
    if (!pendingKeys.value.includes(key)) pendingKeys.value.push(key)
    return
  }
  const delay = cfg.trigger?.delay_ms ?? 600
  window.setTimeout(() => {
    if (guideModalState.open) return
    openGuideModal(key, cfg, false)
  }, delay)
}

export async function openGuideModalByKey(key: string) {
  const cfg = await loadGuideConfig(key)
  if (!cfg) return
  openGuideModal(key, cfg, true)
}

export function flushPendingGuide() {
  const next = pendingKeys.value.shift()
  if (next) void openGuideModalByKey(next)
}
