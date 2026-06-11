import { ref, computed, reactive } from 'vue'

/** 背景动效档位（已无 3D 球场） */
export type PerformanceMode = 'auto' | 'high' | 'balanced' | 'lite'

export interface MatchContext {
  team1: string
  team2: string
  homeScore?: number | null
  awayScore?: number | null
  minute?: number | null
  status?: string
  stadium?: string
  formationDots?: { name: string; x: number; y: number; side: 'home' | 'away' }[]
}

const STORAGE_KEY = 'wc2026_stadium_mode'

let lowBatteryHint = false

if (typeof navigator !== 'undefined' && 'getBattery' in navigator) {
  ;(navigator as Navigator & { getBattery?: () => Promise<{ level: number; charging: boolean; addEventListener?: (e: string, fn: () => void) => void }> })
    .getBattery?.()
    .then((b) => {
      const check = () => {
        lowBatteryHint = !b.charging && b.level < 0.2
      }
      check()
      b.addEventListener?.('levelchange', check)
      b.addEventListener?.('chargingchange', check)
    })
    .catch(() => {})
}

function detectAutoMode(): PerformanceMode {
  if (typeof navigator === 'undefined') return 'balanced'
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return 'lite'
  if (lowBatteryHint) return 'lite'
  const mobile = /Mobi|Android/i.test(navigator.userAgent)
  if (mobile) return 'lite'
  return 'balanced'
}

const performanceMode = ref<PerformanceMode>(
  (localStorage.getItem(STORAGE_KEY) as PerformanceMode) || 'auto',
)

const matchContext = ref<MatchContext | null>(null)
const goalFlash = ref(false)
const analyzing = ref(false)
const heatmapData = ref<number[][] | null>(null)

const uiOverlayKeys = reactive(new Set<string>())

function setUiOverlay(key: string, open: boolean) {
  if (open) uiOverlayKeys.add(key)
  else uiOverlayKeys.delete(key)
}

export function useStadiumStore() {
  const effectiveMode = computed(() => {
    if (performanceMode.value === 'auto') return detectAutoMode()
    return performanceMode.value
  })

  const uiOverlayOpen = computed(() => uiOverlayKeys.size > 0)

  function setPerformanceMode(mode: PerformanceMode) {
    performanceMode.value = mode
    localStorage.setItem(STORAGE_KEY, mode)
  }

  function setMatchContext(ctx: MatchContext | null) {
    matchContext.value = ctx
  }

  function triggerGoalEffect() {
    goalFlash.value = true
    setTimeout(() => {
      goalFlash.value = false
    }, 2000)
  }

  function setAnalyzing(v: boolean) {
    analyzing.value = v
  }

  function setHeatmap(data: number[][] | null) {
    heatmapData.value = data
  }

  function setUiOverlayOpen(v: boolean) {
    setUiOverlay('legacy', v)
  }

  return {
    performanceMode,
    effectiveMode,
    matchContext,
    goalFlash,
    analyzing,
    heatmapData,
    uiOverlayOpen,
    setPerformanceMode,
    setMatchContext,
    triggerGoalEffect,
    setAnalyzing,
    setHeatmap,
    setUiOverlay,
    setUiOverlayOpen,
  }
}
