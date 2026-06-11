import { useLiveMatchesStore } from '@/stores/liveMatchesStore'

/** Read-only access to app-level live matches subscription (see App.vue). */
export function useLiveMatches(_pollMs = 30000) {
  return useLiveMatchesStore()
}
