import { onMounted, onUnmounted } from 'vue'
import { subscribeLiveMatches, useLiveMatchesStore } from '@/stores/liveMatchesStore'

/** Shared live matches singleton — one WebSocket + poll for all consumers. */
export function useLiveMatches(_pollMs = 30000) {
  const store = useLiveMatchesStore()
  let unsubscribe: (() => void) | null = null

  onMounted(() => {
    unsubscribe = subscribeLiveMatches()
  })

  onUnmounted(() => {
    unsubscribe?.()
  })

  return store
}
