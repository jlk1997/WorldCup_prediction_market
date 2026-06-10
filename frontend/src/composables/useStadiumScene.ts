import { useStadiumStore } from '@/stores/stadiumStore'
import type { MatchContext } from '@/stores/stadiumStore'

/** Unified 3D stadium scene control for views. */
export function useStadiumScene() {
  const store = useStadiumStore()

  function setMatchContext(ctx: MatchContext | null) {
    store.setMatchContext(ctx)
  }

  function onScoreChange(prevHome: number | null | undefined, prevAway: number | null | undefined, home: number | null | undefined, away: number | null | undefined) {
    const h0 = prevHome ?? 0
    const a0 = prevAway ?? 0
    const h1 = home ?? 0
    const a1 = away ?? 0
    if (h1 > h0 || a1 > a0) {
      store.triggerGoalEffect()
    }
  }

  return {
    ...store,
    setMatchContext,
    onScoreChange,
  }
}
