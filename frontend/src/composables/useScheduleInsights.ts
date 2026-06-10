import { ref, watch, type Ref } from 'vue'
import { apiClient } from '@/api/client'
import type { AgentInsight, ScheduleItem } from '@/types/api'
import { resolveAgentMode } from '@/composables/useAgentNavigate'

function debounce<T extends (...args: unknown[]) => void>(fn: T, ms: number) {
  let t: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (t) clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}

export function useScheduleInsights(
  matchesRef: Ref<ScheduleItem[]>,
  options?: { enabled?: Ref<boolean> },
) {
  const insightMap = ref<Record<string, AgentInsight>>({})
  const loading = ref(false)
  let lastPairsKey = ''

  function pairKey(team1: string, team2: string) {
    return `${team1}|${team2}`
  }

  async function refresh() {
    if (options?.enabled && !options.enabled.value) return

    const list = matchesRef.value.filter(
      (m) => m.team1 && m.team2 && !m.team1.startsWith('待定'),
    )
    if (!list.length) {
      insightMap.value = {}
      lastPairsKey = ''
      return
    }

    const pairs = list.slice(0, 20).map((m) => ({
      team1: m.team1!,
      team2: m.team2!,
      mode: resolveAgentMode(m),
    }))
    const pairsKey = pairs.map((p) => `${p.team1}|${p.team2}|${p.mode}`).join(';')
    if (pairsKey === lastPairsKey && Object.keys(insightMap.value).length) return
    lastPairsKey = pairsKey

    loading.value = true
    try {
      const res = await apiClient.post<{ data: Record<string, AgentInsight> }>(
        '/api/agent/insights/batch',
        { pairs },
      )
      insightMap.value = res.data.data
    } catch {
      insightMap.value = {}
    } finally {
      loading.value = false
    }
  }

  const debouncedRefresh = debounce(refresh, 800)

  function getInsight(match: ScheduleItem): AgentInsight | null {
    if (!match.team1 || !match.team2) return null
    return insightMap.value[pairKey(match.team1, match.team2)] || null
  }

  watch(
    matchesRef,
    () => {
      debouncedRefresh()
    },
    { immediate: true },
  )

  if (options?.enabled) {
    watch(options.enabled, (on) => {
      if (on) debouncedRefresh()
    })
  }

  return { insightMap, loading, refresh, getInsight }
}
