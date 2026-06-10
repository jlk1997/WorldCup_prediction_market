import { ref, computed, reactive } from 'vue'

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
  if (mobile) return 'balanced'
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

  const useThreeJs = computed(() => effectiveMode.value !== 'lite' && !uiOverlayOpen.value)

  /** 赛事大屏 + 高画质：全特效 3D；其余页面或非高画质：低画质 3D */
  const useHighQuality3D = computed(
    () => effectiveMode.value === 'high',
  )

  const useFullAnalyzePulse = computed(
    () => effectiveMode.value === 'high' || effectiveMode.value === 'auto',
  )

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
    useThreeJs,
    useHighQuality3D,
    useFullAnalyzePulse,
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
