import { nextTick, type Ref } from 'vue'
import { getScrollRoot, scrollElementIntoRootView } from '@/utils/scrollRoot'

/** Scroll predict hall so highlighted match card is visible (page-level scroll). */
export function usePredictHighlightScroll(
  highlightId: Ref<number | null>,
  scrollToIndex?: Ref<number | null>,
) {
  async function scrollToHighlight() {
    const id = highlightId.value
    if (!id) return
    await nextTick()
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    const card = document.querySelector(`[data-match-id="${id}"]`) as HTMLElement | null
    if (!card) return

    await scrollElementIntoRootView(card)
    void scrollToIndex?.value
  }

  return { scrollToHighlight, getScrollRoot }
}
