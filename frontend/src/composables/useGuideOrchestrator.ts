import { reactive } from 'vue'

export const GuidePriority = {
  OnboardingTour: 100,
  SettlementReveal: 90,
  CollectibleReveal: 85,
  GuideModal: 70,
  PredictFirstCoach: 60,
  LeaderboardReward: 50,
  SecondPredictCoach: 40,
} as const

export type GuidePriorityLevel = (typeof GuidePriority)[keyof typeof GuidePriority]

type GuideEntry = {
  priority: GuidePriorityLevel
  isActive: () => boolean
  open: () => void | Promise<void>
}

export const guideOrchestratorState = reactive({
  activeId: null as string | null,
  activePriority: 0,
})

const registry = new Map<string, GuideEntry>()
const pending: { id: string; priority: GuidePriorityLevel }[] = []

function sortPending() {
  pending.sort((a, b) => b.priority - a.priority)
}

export function registerGuide(id: string, entry: GuideEntry) {
  registry.set(id, entry)
}

export function unregisterGuide(id: string) {
  registry.delete(id)
  if (guideOrchestratorState.activeId === id) {
    guideOrchestratorState.activeId = null
    guideOrchestratorState.activePriority = 0
    flushGuideQueue()
  }
}

export function isGuideBlocked(priority: GuidePriorityLevel): boolean {
  if (guideOrchestratorState.activePriority > priority) return true
  for (const entry of registry.values()) {
    if (entry.isActive() && entry.priority > priority) return true
  }
  return false
}

export function notifyGuideOpened(id: string, priority: GuidePriorityLevel) {
  guideOrchestratorState.activeId = id
  guideOrchestratorState.activePriority = Math.max(guideOrchestratorState.activePriority, priority)
}

export function notifyGuideClosed(id: string) {
  if (guideOrchestratorState.activeId === id) {
    guideOrchestratorState.activeId = null
    guideOrchestratorState.activePriority = 0
  }
  flushGuideQueue()
}

export function requestGuide(id: string): boolean {
  const entry = registry.get(id)
  if (!entry) return false
  if (isGuideBlocked(entry.priority)) {
    if (!pending.some((p) => p.id === id)) {
      pending.push({ id, priority: entry.priority })
      sortPending()
    }
    return false
  }
  if (entry.isActive()) return true
  void entry.open()
  return true
}

export function flushGuideQueue() {
  if (guideOrchestratorState.activeId) return
  while (pending.length) {
    const next = pending[0]
    const entry = registry.get(next.id)
    if (!entry || isGuideBlocked(entry.priority)) return
    pending.shift()
    if (entry.isActive()) continue
    void entry.open()
    return
  }
}

export function isAnyGuideOverlayActive(): boolean {
  if (guideOrchestratorState.activeId) return true
  for (const entry of registry.values()) {
    if (entry.isActive()) return true
  }
  return false
}
