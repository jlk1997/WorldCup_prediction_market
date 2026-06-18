import { nextTick, type Ref } from 'vue'

/** Scroll predict hall virtual list so highlighted match card is visible. */
export function usePredictHighlightScroll(
  highlightId: Ref<number | null>,
  scrollToIndex: Ref<number | null>,
  listRootRef: Ref<{ scrollToItem?: (index: number) => void } | null>,
) {
  async function scrollToHighlight() {
    const id = highlightId.value
    if (!id) return
    await nextTick()
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    const idx = scrollToIndex.value
    if (idx != null && idx >= 0) {
      listRootRef.value?.scrollToItem?.(idx)
      return
    }

    const card = document.querySelector(`[data-match-id="${id}"]`) as HTMLElement | null
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' })
      const root = card.closest('.virtual-list') as HTMLElement | null
      if (root && card.offsetTop) {
        root.scrollTop = Math.max(0, card.offsetTop - 80)
      }
    }
  }

  return { scrollToHighlight }
}
